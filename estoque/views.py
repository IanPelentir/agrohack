"""
views.py — AGROGADO: Camada de Apresentação e Lógica de Controle
AgroHack 2026/2 — IFRO Campus Ariquemes

Views implementadas:
  - painel(): Dashboard To-Do List com KPIs, semáforo e simulação sazonal (RF02.1–RF02.3)
  - produto_lista(): Consulta organizada de insumos com filtros e status
  - produto_detalhe(): Ficha detalhada de produto com lotes, alertas e histórico
  - consumo(): Acompanhamento temporal interativo com Chart.js (RF03.6)
  - importar(): Upload e prévia de CSV com 13 campos (RF01.1, RF01.2)
  - confirmar_importacao(): Gravação atômica dos registros validados (RF01.3)
  - movimentacao_nova(): Registro manual com reanálise automática (RF01.3, RN01.1)
  - lote_novo() / lote_editar() / lote_excluir(): Gestão de LoteAnimais
  - carregar_demonstracao(): Carrega dados fictícios para avaliação do AgroHack

Tratamento de exceções aplicado em todas as views:
  - Dados ausentes/None: nunca convertidos em zero (RN02)
  - Unidades incompatíveis: detectadas no clean() e na importação (RN01)
  - Histórico insuficiente: comunicado textualmente (RN03)
  - Saldo negativo: bloqueado com mensagem explicativa (RN01.1)
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .analises import (
    acompanhamento_temporal,
    analisar_validade,
    autonomia_por_rebanho,
    calcular_estoque_critico,
    estimar_duracao,
    gerar_alertas_priorizados,
)
from .forms import (
    AtivoRuralForm,
    ManutencaoAtivoForm,
    PendenciaPrioritariaForm,
    ProdutoForm,
    TransferenciaRecursoForm,
)
from .models import (
    AtivoRural,
    Lote,
    LoteAnimais,
    ManutencaoAtivo,
    Movimentacao,
    PendenciaPrioritaria,
    Produto,
    TransferenciaRecurso,
)


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _mapear_categoria(texto: str) -> str:
    """
    Normaliza string de categoria proveniente do CSV para o código interno de Produto.CATEGORIAS.
    Fallback para 'DEFENSIVOS' se não houver correspondência (documenta suposição).
    """
    if not texto:
        return 'DEFENSIVOS'
    t = texto.upper().strip()
    if any(k in t for k in ['DEFENSIV', 'HERBICIDA', 'FUNGICIDA', 'INSETICIDA']):
        return 'DEFENSIVOS'
    if any(k in t for k in ['FERTILIZ', 'ADUBO', 'CORRETIV', 'CALCAR']):
        return 'FERTILIZANTES'
    if any(k in t for k in ['SEMENT', 'MUDA', 'GRAO']):
        return 'SEMENTES'
    if any(k in t for k in ['MEDIC', 'VACINA', 'VERMIF', 'VETERIN', 'ANTIBIOTIC']):
        return 'MEDICAMENTOS'
    if any(k in t for k in ['COMBUST', 'DIESEL', 'GASOLINA', 'LUBRIF', 'OLEO']):
        return 'COMBUSTIVEIS'
    if any(k in t for k in ['SUPLEMENT', 'SAL', 'RACAO', 'MINERAL', 'PROTEIN']):
        return 'SUPLEMENTOS'
    if any(k in t for k in ['MANUT', 'PECA', 'FERRAMENTA']):
        return 'MANUTENCAO'
    if any(k in t for k in ['EPI', 'EQUIP', 'MASCARA', 'LUVA', 'PROTECAO']):
        return 'EPI'
    chaves = [c[0] for c in Produto.CATEGORIAS]
    if t in chaves:
        return t
    return 'DEFENSIVOS'


def _normalizar_data(texto: str) -> str | None:
    """
    Normaliza string de data para ISO 8601 (YYYY-MM-DD).
    Suporta formatos DD/MM/YYYY e YYYY-MM-DD.
    Retorna None se não conseguir parsear (RN02: ausência não vira data fictícia).
    """
    if not texto or not str(texto).strip():
        return None
    val = str(texto).strip()
    try:
        return date.fromisoformat(val).isoformat()
    except (ValueError, TypeError):
        pass
    try:
        partes = val.split('/')
        if len(partes) == 3:
            return date(int(partes[2]), int(partes[1]), int(partes[0])).isoformat()
    except (ValueError, IndexError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# RF02 — Dashboard To-Do List com KPIs e Simulação Sazonal
# ---------------------------------------------------------------------------

def _alertas_ativos() -> list[dict]:
    alertas = []
    for ativo in AtivoRural.objects.select_related('produto').filter(
        status_manutencao__in=('REVISAO', 'MANUTENCAO', 'INATIVO')
    ):
        prioridade = 'ALTA' if ativo.status_manutencao in ('MANUTENCAO', 'INATIVO') else 'MEDIA'
        alertas.append({
            'tipo': 'MANUTENCAO_ATIVO',
            'tipo_display': f"Ativo: {ativo.get_status_manutencao_display()}",
            'prioridade': prioridade,
            'produto_id': ativo.produto_id,
            'produto_nome': ativo.produto.nome,
            'ativo_id': ativo.id,
            'justificativa': (
                f"{ativo.produto.tipo_item or ativo.produto.nome} está com status "
                f"'{ativo.get_status_manutencao_display()}'. Confira a manutenção e atualize "
                "o status após a intervenção."
            ),
        })
    return alertas


def painel(request, pendencia_form=None):
    """
    RF02.1, RF02.2, RF02.3 — Dashboard principal do AGROGADO.

    Calcula em tempo real (RF01.3):
      - KPIs consolidados (cabeças, alertas por nível, valor em estoque)
      - Alertas priorizados semafóricos via motor analítico determinístico
      - Simulação sazonal (modo_seca=True → fator de consumo 2×)
      - Gestão de lotes de animais com ECC, pasto e cobertura de suplementação
      - Inventário de insumos com status semafórico e cobertura em dias

    Tratamento de exceções:
      - Lotes sem insumo vinculado: status 'SEM_VINCULO' (não gera erro)
      - Saldo None/zero: preservado como zero e comunicado explicitamente (RN02)
      - Peso/ECC ausente: não convertido para valor padrão fictício (RN02)
    """
    # Modo sazonal: ativado via query string ?seca=1
    modo_seca = request.GET.get('seca') in ('1', 'true', 'sim')
    fator_seca = Decimal('2.0') if modo_seca else Decimal('1.0')

    # --- 1. Gestão de Lotes de Animais ---
    lotes_qs = LoteAnimais.objects.filter(ativo=True).select_related('insumo_suplementar')
    lotes_formatados = []
    total_cabecas = 0
    total_consumo_diario_kg = Decimal('0.00')
    peso_total_rebanho = Decimal('0.00')

    for lote in lotes_qs:
        total_cabecas += lote.quantidade_cabecas
        consumo_diario_lote = lote.consumo_diario_total_kg * fator_seca
        total_consumo_diario_kg += consumo_diario_lote

        # Peso médio: preserva None se não informado (RN02)
        peso_medio = lote.peso_medio_estimado
        if peso_medio is not None:
            peso_total_rebanho += peso_medio * Decimal(str(lote.quantidade_cabecas))

        # Autonomia do insumo suplementar para este lote
        duracao_dias = lote.duracao_estimada_insumo(fator_seca=fator_seca)

        # Status semafórico da suplementação
        if duracao_dias is None:
            status_lote, status_cor = 'SEM_VINCULO', 'cinza'
        elif duracao_dias <= 7:
            status_lote, status_cor = 'CRITICO', 'vermelho'
        elif duracao_dias <= 15:
            status_lote, status_cor = 'ATENCAO', 'amarelo'
        else:
            status_lote, status_cor = 'NORMAL', 'verde'

        # ECC: barra de progresso e classificação textual
        ecc_val = float(lote.escore_corporal)
        ecc_percent = min(100, max(10, int((ecc_val / 5.0) * 100)))
        if ecc_val < 3.0:
            ecc_class, ecc_texto = 'baixo', 'Abaixo do Ideal'
        elif ecc_val <= 4.0:
            ecc_class, ecc_texto = 'ideal', 'Ideal / Bom'
        else:
            ecc_class, ecc_texto = 'alto', 'Sobrepeso'

        lotes_formatados.append({
            'id': lote.id,
            'nome': lote.nome,
            'categoria': lote.categoria,
            'categoria_display': lote.get_categoria_display(),
            'quantidade_cabecas': lote.quantidade_cabecas,
            'pasto_localizacao': lote.pasto_localizacao,
            'escore_corporal': lote.escore_corporal,
            'ecc_percent': ecc_percent,
            'ecc_class': ecc_class,
            'ecc_texto': ecc_texto,
            'peso_medio_estimado': peso_medio,  # None preservado (RN02)
            'consumo_diario_cabeca_g': int(lote.consumo_diario_cabeca * 1000 * fator_seca),
            'consumo_diario_total_kg': consumo_diario_lote,
            'insumo_nome': (
                lote.insumo_suplementar.nome if lote.insumo_suplementar else 'Nenhum vinculado'
            ),
            'insumo_id': (
                lote.insumo_suplementar.id if lote.insumo_suplementar else None
            ),
            'duracao_dias': duracao_dias,
            'status_lote': status_lote,
            'status_cor': status_cor,
            'observacoes': lote.observacoes,
        })

    # --- 2. Alertas Priorizados (motor analítico determinístico) ---
    # Passa total de cabeças para análise de campanhas IDARON (RF03.5)
    alertas = gerar_alertas_priorizados(
        modo_seca=modo_seca,
        total_cabecas_propriedade=total_cabecas,
    )
    alertas.extend(_alertas_ativos())
    peso_prioridade = {'ALTA': 1, 'MEDIA': 2, 'BAIXA': 3}
    alertas.sort(key=lambda alerta: peso_prioridade.get(alerta.get('prioridade', 'BAIXA'), 99))
    pendencias_abertas = list(
        PendenciaPrioritaria.objects.filter(concluida=False).select_related('produto', 'ativo__produto')
    )
    for alerta in alertas:
        pendencia = next((
            item for item in pendencias_abertas
            if (
                alerta.get('produto_id') and item.produto_id == alerta.get('produto_id')
            ) or (
                alerta.get('ativo_id') and item.ativo_id == alerta.get('ativo_id')
            )
        ), None)
        alerta['pendencia_aberta_id'] = pendencia.id if pendencia else None

    # Contadores semafóricos para KPIs
    alta_prioridade = sum(1 for a in alertas if a.get('prioridade') == 'ALTA')
    media_prioridade = sum(1 for a in alertas if a.get('prioridade') == 'MEDIA')
    baixa_prioridade = sum(1 for a in alertas if a.get('prioridade') == 'BAIXA')

    # --- 3. Inventário de Insumos ---
    produtos_qs = Produto.objects.filter(ativo=True)
    total_produtos = produtos_qs.count()
    valor_total_estocado = Decimal('0.00')
    produtos_insumos = []
    hoje = date.today()

    for p in produtos_qs:
        saldo = p.saldo_atual
        minimo = p.estoque_minimo
        valor_item = p.valor_total_estoque  # None se sem preço (RN02)
        if valor_item is not None:
            valor_total_estocado += valor_item

        # Agrupamento visual por categoria
        if p.categoria == 'MEDICAMENTOS':
            grupo_categoria, grupo_classe = 'Sanidade', 'sanidade'
        elif p.categoria == 'SUPLEMENTOS':
            grupo_categoria, grupo_classe = 'Nutrição', 'nutricao'
        else:
            grupo_categoria, grupo_classe = 'Manejo', 'manejo'

        # Status semafórico do insumo
        if saldo <= Decimal('0.00') or (minimo is not None and saldo <= minimo):
            status_estoque, status_cor = 'CRITICO', 'vermelho'
        elif minimo is not None and saldo <= (minimo * Decimal('1.5')):
            status_estoque, status_cor = 'ATENCAO', 'amarelo'
        else:
            status_estoque, status_cor = 'NORMAL', 'verde'

        # Próxima validade
        lote_proximo = p.lotes.filter(data_validade__isnull=False).order_by('data_validade').first()
        validade_data = lote_proximo.data_validade if lote_proximo else None
        dias_validade = (validade_data - hoje).days if validade_data else None

        # Cobertura de estoque: preferência pelo consumo zootécnico, fallback histórico
        try:
            cobertura = autonomia_por_rebanho(p, fator_seca=fator_seca)
        except Exception:
            cobertura = estimar_duracao(p)

        # Percentual em relação ao mínimo (para barra de progresso)
        if minimo and minimo > Decimal('0.00'):
            percentual_nivel = min(200, int((float(saldo) / float(minimo)) * 100))
        else:
            percentual_nivel = 100

        produtos_insumos.append({
            'id': p.id,
            'nome': p.nome,
            'categoria_display': p.get_categoria_display(),
            'grupo_categoria': grupo_categoria,
            'grupo_classe': grupo_classe,
            'unidade': p.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'percentual_nivel': percentual_nivel,
            'status_estoque': status_estoque,
            'status_cor': status_cor,
            'preco_unitario': p.preco_referencia,  # None preservado (RN02)
            'valor_total': valor_item,              # None preservado (RN02)
            'validade': validade_data,
            'dias_validade': dias_validade,
            'cobertura_dias': cobertura.get('dias'),
            'cobertura_fonte': cobertura.get('fonte', 'historico_saidas'),
        })

    # --- 4. KPIs Pecuários ---
    # Cotação referencial da arroba do boi gordo (Ariquemes/RO — valor simulado para demonstração)
    cotacao_arroba = Decimal('228.50')
    # Rendimento de carcaça ~50% (@=15 kg carcaça = 30 kg peso vivo)
    arrobas_totais = (
        (peso_total_rebanho / Decimal('30.00'))
        if total_cabecas > 0 and peso_total_rebanho > Decimal('0.00')
        else Decimal('0.00')
    )
    patrimonio_rebanho = arrobas_totais * cotacao_arroba

    context = {
        'alertas': alertas,
        'pendencia_form': pendencia_form or PendenciaPrioritariaForm(),
        'pendencias_abertas': pendencias_abertas,
        'pendencias_concluidas': PendenciaPrioritaria.objects.filter(concluida=True).select_related(
            'produto', 'ativo__produto'
        )[:10],
        'lotes_animais': lotes_formatados,
        'produtos_insumos': produtos_insumos,
        'modo_seca': modo_seca,
        'kpis': {
            'alta_prioridade': alta_prioridade,
            'media_prioridade': media_prioridade,
            'baixa_prioridade': baixa_prioridade,
            'total_alertas': len(alertas),
            'total_produtos': total_produtos,
            'total_cabecas': total_cabecas,
            'total_lotes': len(lotes_formatados),
            'total_consumo_diario_kg': total_consumo_diario_kg,
            'valor_total_estocado': valor_total_estocado,
            'cotacao_arroba': cotacao_arroba,
            'patrimonio_rebanho': patrimonio_rebanho,
            'arrobas_totais': arrobas_totais,
        },
        'total_alertas_urgentes': alta_prioridade,
    }
    return render(request, 'estoque/painel.html', context)


# ---------------------------------------------------------------------------
# Consulta de Produtos / Insumos
# ---------------------------------------------------------------------------

def produto_lista(request):
    """
    Consulta organizada de insumos com filtros de busca, categoria e status.
    """
    busca = request.GET.get('busca', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    status = request.GET.get('status', '').strip()

    qs = Produto.objects.filter(ativo=True)
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(tipo_item__icontains=busca))
    if categoria:
        qs = qs.filter(categoria=categoria)

    produtos_formatados = []
    for p in qs:
        saldo = p.saldo_atual
        minimo = p.estoque_minimo

        if saldo <= Decimal('0.00') or (minimo is not None and saldo <= minimo):
            status_estoque = 'CRITICO'
        elif minimo is not None and saldo <= (minimo * Decimal('1.5')):
            status_estoque = 'ATENCAO'
        else:
            status_estoque = 'NORMAL'

        if status:
            if status == 'critico' and status_estoque != 'CRITICO':
                continue
            if status == 'atencao' and status_estoque != 'ATENCAO':
                continue
            if status == 'normal' and status_estoque != 'NORMAL':
                continue

        duracao = estimar_duracao(p)
        produtos_formatados.append({
            'id': p.id,
            'nome': p.nome,
            'tipo_item': p.tipo_item,
            'categoria': p.get_categoria_display(),
            'unidade': p.unidade,
            'tipo_embalagem': p.get_tipo_embalagem_display(),
            'embalagem_em_caixa': p.embalagem_em_caixa,
            'peso_embalagem_kg': p.peso_embalagem_kg,
            'volume_embalagem_ml': p.volume_embalagem_ml,
            'fabricante': p.fabricante,
            'modelo': p.modelo,
            'numero_serie': p.numero_serie,
            'placa': p.placa,
            'chassi': p.chassi,
            'ano_fabricacao': p.ano_fabricacao,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'status_estoque': status_estoque,
            'cobertura_dias': duracao.get('dias'),
            'preco_unitario': p.preco_referencia,
            'valor_total': p.valor_total_estoque,
        })

    context = {
        'produtos': produtos_formatados,
        'categorias': Produto.CATEGORIAS,
        'busca_atual': busca,
        'categoria_selecionada': categoria,
        'status_selecionado': status,
    }
    return render(request, 'estoque/produto_lista.html', context)


def produto_novo(request):
    """Cadastra um insumo, medicamento, implemento ou máquina da propriedade."""
    form = ProdutoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        produto = form.save()
        if produto.categoria in ('MAQUINAS', 'VEICULOS'):
            AtivoRural.objects.get_or_create(produto=produto)
        messages.success(request, f"Produto '{produto.nome}' cadastrado no catálogo da fazenda.")
        return redirect('estoque:produto_lista')
    return render(request, 'estoque/produto_form.html', {'form': form})


# ---------------------------------------------------------------------------
# Ficha Detalhada de Produto
# ---------------------------------------------------------------------------

def produto_detalhe(request, pk):
    """
    Ficha detalhada do insumo: lotes de validade, histórico de movimentações,
    alertas específicos e metodologia de cálculo auditável (RF02.3).
    """
    p = get_object_or_404(Produto, pk=pk)
    saldo = p.saldo_atual
    minimo = p.estoque_minimo
    hoje = date.today()

    if saldo <= Decimal('0.00') or (minimo is not None and saldo <= minimo):
        status_estoque = 'CRITICO'
    elif minimo is not None and saldo <= (minimo * Decimal('1.5')):
        status_estoque = 'ATENCAO'
    else:
        status_estoque = 'NORMAL'

    duracao = estimar_duracao(p)

    # Lotes de validade do produto
    lotes_qs = p.lotes.all()
    lotes_formatados = []
    menor_dias_validade = None
    proxima_validade = None

    for lot in lotes_qs:
        dias = (lot.data_validade - hoje).days if lot.data_validade else None
        vencido = dias is not None and dias < 0
        proximo = dias is not None and 0 <= dias <= 30

        if lot.data_validade and (menor_dias_validade is None or dias < menor_dias_validade):
            menor_dias_validade = dias
            proxima_validade = lot.data_validade

        lotes_formatados.append({
            'numero': lot.numero_lote,
            'data_validade': lot.data_validade,
            'quantidade': lot.saldo_lote,
            'vencido': vencido,
            'proximo_vencimento': proximo,
        })

    # Alertas específicos deste produto
    todos_alertas = gerar_alertas_priorizados()
    alertas_produto = [a for a in todos_alertas if a.get('produto_id') == p.id]

    # Histórico recente (últimas 30 movimentações)
    movs = p.movimentacoes.select_related('lote').all()[:30]

    context = {
        'produto': {
            'id': p.id,
            'nome': p.nome,
            'categoria': p.get_categoria_display(),
            'tipo_item': p.tipo_item,
            'unidade': p.unidade,
            'tipo_embalagem': p.get_tipo_embalagem_display(),
            'embalagem_em_caixa': p.embalagem_em_caixa,
            'peso_embalagem_kg': p.peso_embalagem_kg,
            'volume_embalagem_ml': p.volume_embalagem_ml,
            'fabricante': p.fabricante,
            'modelo': p.modelo,
            'numero_serie': p.numero_serie,
            'placa': p.placa,
            'chassi': p.chassi,
            'ano_fabricacao': p.ano_fabricacao,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'status_estoque': status_estoque,
            'cobertura_dias': duracao.get('dias'),
            'cobertura_justificativa': duracao.get('justificativa'),
            'consumo_medio_diario': duracao.get('consumo_diario'),
            'proxima_validade': proxima_validade,
            'dias_para_vencer': menor_dias_validade,
            'preco_unitario': p.preco_referencia,
            'valor_total': p.valor_total_estoque,
        },
        'alertas_produto': alertas_produto,
        'lotes': lotes_formatados,
        'movimentacoes': [
            {
                'data': m.data_movimentacao,
                'tipo': m.tipo,
                'quantidade': m.quantidade,
                'lote': m.lote.numero_lote if m.lote else '',
                'destino': m.destino,
                'responsavel': m.responsavel,
                'preco_unitario': m.preco_unitario,
                'fornecedor': m.fornecedor,
                'comprador': m.comprador,
                'valor_total_pago': m.valor_total_pago,
                'odometro_km': m.odometro_km,
                'horimetro_h': m.horimetro_h,
            }
            for m in movs
        ],
    }
    return render(request, 'estoque/produto_detalhe.html', context)


# ---------------------------------------------------------------------------
# RF03.6 — Acompanhamento Temporal de Consumo
# ---------------------------------------------------------------------------

def consumo(request):
    """
    RF03.6 — Visualização temporal do consumo por produto com Chart.js.
    Permite identificar sazonalidades agrícolas e pecuárias.
    """
    produtos = Produto.objects.filter(ativo=True)
    produto_id = request.GET.get('produto_id')

    produto_selecionado = None
    if produto_id:
        produto_selecionado = produtos.filter(id=produto_id).first()
    if not produto_selecionado and produtos.exists():
        produto_selecionado = produtos.first()

    chart_labels, chart_data, dados_temporais = [], [], []

    if produto_selecionado:
        dados = acompanhamento_temporal(produto_selecionado)
        chart_labels = dados['labels']
        chart_data = dados['valores']
        dados_temporais = dados['dados_tabela']

    context = {
        'lista_produtos': [{'id': p.id, 'nome': p.nome, 'unidade': p.unidade} for p in produtos],
        'produto_selecionado': {
            'id': produto_selecionado.id,
            'nome': produto_selecionado.nome,
            'unidade': produto_selecionado.unidade,
            'saldo': produto_selecionado.saldo_atual,
        } if produto_selecionado else None,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'dados_temporais': dados_temporais,
    }
    return render(request, 'estoque/consumo.html', context)


def consumo_produto(request, pk):
    return redirect(f"/consumo/?produto_id={pk}")


# ---------------------------------------------------------------------------
# RF01.1 / RF01.2 — Importação CSV com 13 Campos Oficiais
# ---------------------------------------------------------------------------

def importar(request):
    """
    RF01.1, RF01.2 — Upload e prévia de CSV com validação linha a linha.
    Suporta delimitadores , e ; com fallback automático.
    Aplica RN01 (conflito de unidades) e RN02 (preservação de None).
    """
    previa_importacao = None

    if request.method == 'POST' and request.FILES.get('arquivo_csv'):
        arquivo = request.FILES['arquivo_csv']

        if not arquivo.name.lower().endswith('.csv'):
            messages.error(request, "Formato inválido. Envie um arquivo com extensão .csv.")
            return render(request, 'estoque/importar.html', {'previa_importacao': None})

        # Decodificação com fallback de encoding
        conteudo_raw = arquivo.read()
        texto_csv = None
        for enc in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
            try:
                texto_csv = conteudo_raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not texto_csv:
            messages.error(request, "Não foi possível decodificar o arquivo. Verifique a codificação (UTF-8 recomendado).")
            return render(request, 'estoque/importar.html', {'previa_importacao': None})

        primeira_linha = texto_csv.splitlines()[0] if texto_csv.splitlines() else ''
        delimitador = ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','
        leitor = csv.DictReader(io.StringIO(texto_csv), delimiter=delimitador)

        # Mapa de aliases para os 13 campos do regulamento (RF01.2)
        mapa_campos = {
            'produto':           ['produto', 'nome', 'insumo', 'item'],
            'categoria':         ['categoria', 'tipo_produto', 'setor'],
            'unidade':           ['unidade', 'un', 'und', 'unidade_medida'],
            'quantidade':        ['quantidade', 'qtd', 'volume', 'quant'],
            'estoque_minimo':    ['estoque_minimo', 'minimo', 'est_min', 'estoque_min'],
            'tipo_movimentacao': ['tipo_movimentacao', 'tipo', 'operacao', 'movimentacao'],
            'data_movimentacao': ['data_movimentacao', 'data', 'dt_mov', 'data_mov'],
            'preco_aquisicao':   ['preco_aquisicao', 'preco_unitario', 'preco', 'custo', 'valor_unitario'],
            'lote':              ['lote', 'num_lote', 'numero_lote'],
            'data_validade':     ['data_validade', 'validade', 'dt_val', 'vencimento'],
            'fornecedor':        ['fornecedor', 'empresa', 'origem'],
            'destino':           ['destino', 'setor_destino', 'talhao', 'pasto', 'lote_animal'],
            'responsavel':       ['responsavel', 'operador', 'colaborador', 'usuario'],
        }

        produtos_existentes = {p.nome.lower().strip(): p for p in Produto.objects.all()}
        linhas_previa = []
        linhas_validas = []
        erros_gerais = []
        num_linha = 1

        for row in leitor:
            num_linha += 1
            row_clean = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items() if k}

            def obter(chave: str) -> str:
                for alias in mapa_campos.get(chave, []):
                    if alias in row_clean and row_clean[alias]:
                        return row_clean[alias]
                return ''

            produto_nome   = obter('produto')
            categoria_str  = obter('categoria')
            unidade_str    = obter('unidade')
            qtd_str        = obter('quantidade')
            tipo_mov       = obter('tipo_movimentacao').upper()
            data_mov_str   = obter('data_movimentacao')
            est_min_str    = obter('estoque_minimo')
            preco_str      = obter('preco_aquisicao')
            lote_str       = obter('lote')
            validade_str   = obter('data_validade')
            fornecedor_str = obter('fornecedor')
            destino_str    = obter('destino')
            responsavel_str = obter('responsavel')

            valido = True
            motivo_invalido = ''

            if not produto_nome:
                valido = False
                motivo_invalido = 'Nome do produto não informado'
            elif not unidade_str:
                valido = False
                motivo_invalido = 'Unidade de medida não informada'
            else:
                # RN01: conflito de unidades com produto já cadastrado
                p_exist = produtos_existentes.get(produto_nome.lower())
                if p_exist and p_exist.unidade.lower() != unidade_str.lower():
                    valido = False
                    motivo_invalido = (
                        f"Conflito de unidade (RN01): produto '{produto_nome}' já cadastrado "
                        f"em '{p_exist.unidade}', arquivo informa '{unidade_str}'."
                    )

            # Normalização do tipo de movimentação
            if tipo_mov in ('ENTRADA', 'E', 'IN', 'COMPRA', 'RECEBIMENTO'):
                tipo_mov = 'ENTRADA'
            elif tipo_mov in ('SAIDA', 'SAÍDA', 'S', 'OUT', 'CONSUMO', 'APLICACAO', 'APLICAÇÃO'):
                tipo_mov = 'SAIDA'
            else:
                valido = False
                motivo_invalido = f"Tipo de movimentação inválido ('{tipo_mov}')"

            # Quantidade
            qtd_decimal = None
            try:
                qtd_limpa = (
                    qtd_str.replace('.', '').replace(',', '.')
                    if ',' in qtd_str and '.' in qtd_str
                    else qtd_str.replace(',', '.')
                )
                qtd_decimal = Decimal(qtd_limpa)
                if qtd_decimal <= Decimal('0.00'):
                    valido = False
                    motivo_invalido = 'Quantidade deve ser maior que zero'
            except (InvalidOperation, ValueError):
                valido = False
                motivo_invalido = f"Quantidade numérica inválida ('{qtd_str}')"

            # Campos opcionais: preservados como None se ausentes/inválidos (RN02)
            est_min_dec = None
            if est_min_str:
                try:
                    est_min_dec = str(Decimal(est_min_str.replace(',', '.')))
                except (InvalidOperation, ValueError):
                    pass

            preco_dec = None
            if preco_str:
                try:
                    preco_dec = str(Decimal(preco_str.replace(',', '.')))
                except (InvalidOperation, ValueError):
                    pass

            data_mov_norm = _normalizar_data(data_mov_str) or date.today().isoformat()
            validade_norm = _normalizar_data(validade_str)  # None se ausente (RN02)

            linha_dict = {
                'linha_num': num_linha,
                'produto': produto_nome,
                'categoria': categoria_str or 'Geral',
                'categoria_codigo': _mapear_categoria(categoria_str),
                'unidade': unidade_str,
                'quantidade': str(qtd_decimal) if qtd_decimal else qtd_str,
                'tipo_movimentacao': tipo_mov,
                'data_movimentacao': data_mov_norm,
                'estoque_minimo': est_min_dec,
                'data_validade': validade_norm,
                'preco_aquisicao': preco_dec,
                'lote': lote_str,
                'fornecedor': fornecedor_str,
                'destino': destino_str,
                'responsavel': responsavel_str,
                'valido': valido,
                'motivo_invalido': motivo_invalido,
            }
            linhas_previa.append(linha_dict)
            if valido:
                linhas_validas.append(linha_dict)
            else:
                erros_gerais.append(f"Linha {num_linha} ({produto_nome or 'Item'}): {motivo_invalido}")

        request.session['previa_importacao_linhas'] = linhas_validas
        previa_importacao = {
            'total_linhas': len(linhas_previa),
            'erros': erros_gerais[:10],
            'linhas': linhas_previa[:50],
            'total_validas': len(linhas_validas),
        }

    return render(request, 'estoque/importar.html', {'previa_importacao': previa_importacao})


# ---------------------------------------------------------------------------
# RF01.3 — Confirmação e Gravação Atômica da Importação
# ---------------------------------------------------------------------------

def confirmar_importacao(request):
    """
    RF01.3 — Gravação atômica dos registros pré-validados.
    Usa transaction.atomic() para garantir consistência.
    Limpa a sessão após gravação segura.
    """
    if request.method == 'POST':
        linhas = request.session.get('previa_importacao_linhas', [])
        if not linhas:
            messages.warning(request, "Nenhum registro pendente. Selecione um arquivo CSV novamente.")
            return redirect('estoque:importar')

        total_criadas = 0
        with transaction.atomic():
            for l in linhas:
                produto, criado = Produto.objects.get_or_create(
                    nome=l['produto'],
                    defaults={
                        'categoria': l['categoria_codigo'],
                        'unidade': l['unidade'],
                        'estoque_minimo': Decimal(l['estoque_minimo']) if l.get('estoque_minimo') else None,
                        'preco_referencia': Decimal(l['preco_aquisicao']) if l.get('preco_aquisicao') else None,
                    }
                )
                if not criado:
                    salvar = False
                    if l.get('estoque_minimo') and produto.estoque_minimo is None:
                        produto.estoque_minimo = Decimal(l['estoque_minimo'])
                        salvar = True
                    if l.get('preco_aquisicao') and produto.preco_referencia is None:
                        produto.preco_referencia = Decimal(l['preco_aquisicao'])
                        salvar = True
                    if salvar:
                        produto.save()

                lote = None
                if l.get('lote'):
                    data_val = date.fromisoformat(l['data_validade']) if l.get('data_validade') else None
                    lote, _ = Lote.objects.get_or_create(
                        produto=produto,
                        numero_lote=l['lote'],
                        defaults={'data_validade': data_val},
                    )
                    if data_val and not lote.data_validade:
                        lote.data_validade = data_val
                        lote.save()

                data_mov = (
                    date.fromisoformat(l['data_movimentacao'])
                    if l.get('data_movimentacao') else date.today()
                )
                Movimentacao.objects.create(
                    produto=produto,
                    lote=lote,
                    tipo=l['tipo_movimentacao'],
                    quantidade=Decimal(l['quantidade']),
                    data_movimentacao=data_mov,
                    preco_unitario=Decimal(l['preco_aquisicao']) if l.get('preco_aquisicao') else None,
                    fornecedor=l.get('fornecedor', ''),
                    destino=l.get('destino', ''),
                    responsavel=l.get('responsavel', ''),
                )
                total_criadas += 1

        if 'previa_importacao_linhas' in request.session:
            del request.session['previa_importacao_linhas']

        messages.success(
            request,
            f"Importação concluída com sucesso: {total_criadas} registro(s) gravado(s). "
            f"O motor analítico recalculou todos os diagnósticos em tempo real (RF01.3)."
        )
        return redirect('estoque:painel')

    return redirect('estoque:importar')


# ---------------------------------------------------------------------------
# RF01.3 — Registro Manual de Movimentação
# ---------------------------------------------------------------------------

def movimentacao_nova(request):
    """
    RF01.3 — Registro manual de movimentação com validação RN01.1 (saldo negativo).
    Após gravação, redireciona para o painel disparando reanálise automática.
    """
    produtos = list(Produto.objects.filter(ativo=True))
    ativos = list(AtivoRural.objects.select_related('produto').filter(produto__ativo=True))
    ativos_contexto = [
        {'id': ativo.id, 'nome': ativo.produto.nome, 'tipo_item': ativo.produto.tipo_item}
        for ativo in ativos
    ]
    produtos_contexto = [
        {
            'id': p.id,
            'nome': p.nome,
            'unidade': p.unidade,
            'saldo': p.saldo_atual,
            'tipo_item': p.tipo_item,
            'categoria': p.categoria,
            'categoria_display': p.get_categoria_display(),
            'tipo_embalagem': p.get_tipo_embalagem_display(),
            'embalagem_em_caixa': p.embalagem_em_caixa,
            'peso_embalagem_kg': p.peso_embalagem_kg,
            'volume_embalagem_ml': p.volume_embalagem_ml,
            'fabricante': p.fabricante,
            'modelo': p.modelo,
            'numero_serie': p.numero_serie,
            'placa': p.placa,
            'chassi': p.chassi,
            'ano_fabricacao': p.ano_fabricacao,
        }
        for p in produtos
    ]

    if request.method == 'POST':
        produto_id    = request.POST.get('produto')
        tipo          = request.POST.get('tipo')
        quantidade_str = request.POST.get('quantidade', '').strip()
        data_str      = request.POST.get('data_movimentacao', request.POST.get('data', '')).strip()
        lote_num      = request.POST.get('lote', '').strip()
        validade_str  = request.POST.get('validade', '').strip()
        preco_str     = request.POST.get('preco_unitario', '').strip()
        destino       = request.POST.get('destino', '').strip()
        responsavel   = request.POST.get('responsavel', '').strip()
        fornecedor    = request.POST.get('fornecedor', '').strip()
        comprador     = request.POST.get('comprador', '').strip()
        valor_total_str = request.POST.get('valor_total_pago', '').strip()
        odometro_str  = request.POST.get('odometro_km', '').strip()
        horimetro_str = request.POST.get('horimetro_h', '').strip()
        ativo_id      = request.POST.get('ativo', '').strip()
        origem_recurso = request.POST.get('origem_recurso', 'COMPRA_EXTERNA')

        produto = get_object_or_404(Produto, id=produto_id)
        eh_ativo = produto.categoria in ('MAQUINAS', 'VEICULOS', 'FERRAMENTAS')
        ativo_relacionado = get_object_or_404(AtivoRural, pk=ativo_id) if ativo_id else None

        ctx_erro = {
            'produtos': produtos_contexto,
            'produto_selecionado_id': produto_id,
            'tipo_selecionado': tipo,
            'data_padrao': data_str or date.today().isoformat(),
            'form_values': request.POST,
            'ativos': ativos_contexto,
            'origens_recurso': Movimentacao.ORIGENS_RECURSO,
        }

        if tipo not in ('ENTRADA', 'SAIDA'):
            messages.error(request, "Selecione se a operação é uma entrada ou uma saída.")
            return render(request, 'estoque/movimentacao_form.html', ctx_erro)

        origens_validas = {choice[0] for choice in Movimentacao.ORIGENS_RECURSO}
        if origem_recurso not in origens_validas:
            messages.error(request, "Selecione uma origem válida para o recurso.")
            return render(request, 'estoque/movimentacao_form.html', ctx_erro)

        try:
            quantidade = Decimal(quantidade_str.replace(',', '.'))
            if quantidade <= Decimal('0.00'):
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, "Quantidade inválida. Informe um valor numérico positivo.")
            return render(request, 'estoque/movimentacao_form.html', ctx_erro)

        if eh_ativo and quantidade != quantidade.to_integral_value():
            messages.error(request, "Máquinas, veículos e ferramentas são controlados por unidade inteira.")
            return render(request, 'estoque/movimentacao_form.html', ctx_erro)

        if produto.categoria != 'VEICULOS':
            odometro_str = ''
        if produto.categoria != 'MAQUINAS':
            horimetro_str = ''
        try:
            odometro = Decimal(odometro_str.replace(',', '.')) if odometro_str else None
            horimetro = Decimal(horimetro_str.replace(',', '.')) if horimetro_str else None
            if (odometro is not None and odometro < 0) or (horimetro is not None and horimetro < 0):
                raise InvalidOperation
        except InvalidOperation:
            messages.error(request, "Informe uma leitura válida e não negativa para o medidor do ativo.")
            return render(request, 'estoque/movimentacao_form.html', ctx_erro)

        # RN01.1 — Bloqueio de saldo negativo
        if tipo == 'SAIDA':
            saldo_atual = produto.saldo_atual
            if quantidade > saldo_atual:
                messages.error(
                    request,
                    f"Operação não permitida (RN01.1): Saída de {quantidade} {produto.unidade} "
                    f"excede o saldo disponível ({saldo_atual} {produto.unidade}). "
                    f"O sistema não permite saldo negativo."
                )
                return render(request, 'estoque/movimentacao_form.html', ctx_erro)

        if eh_ativo:
            lote_num = ''
            validade_str = ''
        elif tipo == 'SAIDA':
            validade_str = ''
        if tipo == 'SAIDA':
            preco_str = ''
            valor_total_str = ''
            fornecedor = ''
            comprador = ''
            origem_recurso = 'TRANSFERENCIA_INTERNA'

        lote = None
        if lote_num and tipo == 'SAIDA':
            lote = produto.lotes.filter(numero_lote=lote_num).first()
            if lote is None:
                messages.error(request, "O lote informado não está cadastrado para este produto e não pode ser usado em uma saída.")
                return render(request, 'estoque/movimentacao_form.html', ctx_erro)
            if quantidade > lote.saldo_lote:
                messages.error(
                    request,
                    f"Saída não permitida: o lote {lote_num} possui saldo de {lote.saldo_lote} {produto.unidade}.",
                )
                return render(request, 'estoque/movimentacao_form.html', ctx_erro)
        elif lote_num:
            data_val = date.fromisoformat(validade_str) if validade_str else None
            lote, _ = Lote.objects.get_or_create(
                produto=produto,
                numero_lote=lote_num,
                defaults={'data_validade': data_val},
            )
            if data_val and not lote.data_validade:
                lote.data_validade = data_val
                lote.save()

        preco = Decimal(preco_str.replace(',', '.')) if preco_str else None
        valor_total = Decimal(valor_total_str.replace(',', '.')) if valor_total_str else None

        Movimentacao.objects.create(
            produto=produto,
            lote=lote,
            tipo=tipo,
            quantidade=quantidade,
            data_movimentacao=date.fromisoformat(data_str) if data_str else timezone.now().date(),
            preco_unitario=preco,
            destino=destino,
            responsavel=responsavel,
            fornecedor=fornecedor,
            comprador=comprador,
            valor_total_pago=valor_total,
            odometro_km=odometro,
            horimetro_h=horimetro,
            ativo=ativo_relacionado,
            origem_recurso=origem_recurso,
        )

        messages.success(
            request,
            f"Movimentação de {tipo.lower()} ({quantidade} {produto.unidade}) registrada! "
            f"Diagnósticos e alertas recalculados em tempo real (RF01.3)."
        )
        return redirect('estoque:painel')

    context = {
        'produtos': produtos_contexto,
        'produto_selecionado_id': (
            int(request.GET.get('produto_id', 0))
            if request.GET.get('produto_id')
            else ''
        ),
        'tipo_selecionado': request.GET.get('tipo', 'SAIDA'),
        'data_padrao': date.today().isoformat(),
        'form_values': {},
        'ativos': ativos_contexto,
        'origens_recurso': Movimentacao.ORIGENS_RECURSO,
    }
    return render(request, 'estoque/movimentacao_form.html', context)


def pendencia_nova(request):
    initial = {
        key: request.GET[key]
        for key in ('titulo', 'descricao', 'prioridade', 'produto', 'ativo')
        if request.GET.get(key)
    }
    form = PendenciaPrioritariaForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        pendencia = form.save()
        messages.success(request, f"Pendência '{pendencia.titulo}' adicionada ao painel.")
        return redirect('/#secao-todo')
    if request.method == 'POST':
        messages.error(request, 'Revise os dados da nova pendência.')
    return painel(request, pendencia_form=form)


def pendencia_status(request, pk):
    if request.method != 'POST':
        return redirect('/#secao-todo')

    pendencia = get_object_or_404(PendenciaPrioritaria, pk=pk)
    concluida = request.POST.get('concluida') == 'true'
    pendencia.concluida = concluida
    pendencia.concluida_em = timezone.now() if concluida else None
    pendencia.save(update_fields=['concluida', 'concluida_em'])

    if concluida:
        alertas_atuais = gerar_alertas_priorizados()
        alertas_atuais.extend(_alertas_ativos())
        relacionados = [
            alerta for alerta in alertas_atuais
            if (
                pendencia.produto_id and alerta.get('produto_id') == pendencia.produto_id
            ) or (
                pendencia.ativo_id and alerta.get('ativo_id') == pendencia.ativo_id
            )
        ]
        if relacionados:
            prioridade = {'ALTA': 0, 'MEDIA': 1, 'BAIXA': 2}
            alerta = min(relacionados, key=lambda item: prioridade.get(item.get('prioridade'), 3))
            messages.warning(
                request,
                f"Tarefa '{pendencia.titulo}' concluída; alerta '{alerta['tipo_display']}' "
                f"continua ativo para {alerta.get('produto_nome', 'o ativo')} e foi recalculado. "
                "Atualize o estoque ou o status de manutenção para resolvê-lo."
            )
        else:
            messages.success(
                request,
                f"Tarefa '{pendencia.titulo}' concluída. Recalculamos os alertas e não há "
                "alerta ativo para o item vinculado."
            )
    else:
        messages.info(request, f"Tarefa '{pendencia.titulo}' reaberta.")
    return redirect('/#secao-todo')


def recursos(request, transferencia_form=None, manutencao_form=None):
    produtos_ativos = Produto.objects.filter(ativo=True, categoria__in=('MAQUINAS', 'VEICULOS'))
    for produto in produtos_ativos:
        AtivoRural.objects.get_or_create(produto=produto)

    ativos = AtivoRural.objects.select_related('produto').prefetch_related('manutencoes').all()
    context = {
        'ativos': ativos,
        'status_manutencao_choices': AtivoRural.STATUS_MANUTENCAO,
        'unidades_consumo_choices': AtivoRural.UNIDADES_CONSUMO,
        'manutencoes': ManutencaoAtivo.objects.select_related('ativo__produto')[:12],
        'transferencias': TransferenciaRecurso.objects.select_related(
            'produto_origem', 'produto_destino'
        )[:12],
        'movimentacoes_ativos': Movimentacao.objects.filter(ativo__isnull=False).select_related(
            'produto', 'ativo__produto'
        )[:12],
        'manutencao_form': manutencao_form or ManutencaoAtivoForm(initial={'data': date.today()}),
        'transferencia_form': transferencia_form or TransferenciaRecursoForm(initial={'data': date.today()}),
    }
    return render(request, 'estoque/recursos.html', context)


def ativo_atualizar(request, pk):
    ativo = get_object_or_404(AtivoRural, pk=pk)
    if request.method != 'POST':
        return redirect('estoque:recursos')

    form = AtivoRuralForm(request.POST, instance=ativo)
    if form.is_valid():
        form.save()
        messages.success(request, f"Status e consumo de '{ativo.produto.nome}' atualizados.")
        return redirect('estoque:recursos')

    messages.error(request, 'Revise o status e o consumo médio do ativo.')
    return recursos(request)


def manutencao_nova(request):
    if request.method != 'POST':
        return redirect('estoque:recursos')

    form = ManutencaoAtivoForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            manutencao = form.save()
            ativo = manutencao.ativo
            ativo.status_manutencao = 'OPERACIONAL'
            ativo.save(update_fields=['status_manutencao', 'atualizado_em'])
        messages.success(request, f"Manutenção registrada para '{ativo.produto.nome}'.")
        return redirect('estoque:recursos')

    messages.error(request, 'Revise os dados da manutenção.')
    return recursos(request, manutencao_form=form)


def transferencia_nova(request):
    if request.method != 'POST':
        return redirect('estoque:recursos')

    form = TransferenciaRecursoForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Revise a origem, o destino e as quantidades da transferência.')
        return recursos(request, transferencia_form=form)

    dados = form.cleaned_data
    produto_origem = dados['produto_origem']
    produto_destino = dados['produto_destino']
    quantidade_origem = dados['quantidade_origem']
    quantidade_destino = dados['quantidade_destino']
    origem_movimentacao = (
        dados['origem_recurso']
        if dados['origem_recurso'] != 'MISTO'
        else 'TRANSFERENCIA_INTERNA'
    )
    destino_movimentacao = (
        'PRODUCAO_PROPRIA'
        if dados['destino_tipo'] == 'PRODUCAO_PROPRIA'
        else 'TRANSFERENCIA_INTERNA'
    )

    with transaction.atomic():
        produto_origem = Produto.objects.select_for_update().get(pk=produto_origem.pk)
        saldo_atual = produto_origem.saldo_atual
        if quantidade_origem > saldo_atual:
            form.add_error(
                'quantidade_origem',
                f'Saldo atualizado: {saldo_atual} {produto_origem.unidade}.'
            )
        else:
            saida = Movimentacao.objects.create(
                produto=produto_origem,
                tipo='SAIDA',
                quantidade=quantidade_origem,
                data_movimentacao=dados['data'],
                destino=produto_destino.nome,
                responsavel=dados['responsavel'],
                origem_recurso=origem_movimentacao,
            )
            entrada = Movimentacao.objects.create(
                produto=produto_destino,
                tipo='ENTRADA',
                quantidade=quantidade_destino,
                data_movimentacao=dados['data'],
                destino=dados['local_destino'],
                responsavel=dados['responsavel'],
                origem_recurso=destino_movimentacao,
            )
            TransferenciaRecurso.objects.create(
                produto_origem=produto_origem,
                produto_destino=produto_destino,
                quantidade_origem=quantidade_origem,
                quantidade_destino=quantidade_destino,
                origem_recurso=dados['origem_recurso'],
                destino_tipo=dados['destino_tipo'],
                data=dados['data'],
                local_destino=dados['local_destino'],
                responsavel=dados['responsavel'],
                observacoes=dados['observacoes'],
                movimentacao_saida=saida,
                movimentacao_entrada=entrada,
            )

    if form.errors:
        messages.error(request, 'O saldo mudou durante a operação; a transferência não foi gravada.')
        return recursos(request, transferencia_form=form)

    messages.success(
        request,
        f"Conversão registrada: {quantidade_origem} {produto_origem.unidade} de "
        f"'{produto_origem.nome}' geraram {quantidade_destino} {produto_destino.unidade} "
        f"de '{produto_destino.nome}'."
    )
    return redirect('estoque:recursos')


# ---------------------------------------------------------------------------
# RF03.4 — Gestão de Lotes de Animais
# ---------------------------------------------------------------------------

def lote_novo(request):
    """Cadastro de novo lote de animais (LoteAnimais)."""
    from .forms import LoteAnimaisForm
    if request.method == 'POST':
        form = LoteAnimaisForm(request.POST)
        if form.is_valid():
            lote = form.save()
            messages.success(
                request,
                f"Lote '{lote.nome}' ({lote.quantidade_cabecas} cabeças) cadastrado! "
                f"Motor analítico recalculado para o novo rebanho."
            )
            return redirect('estoque:painel')
        messages.error(request, "Erro ao cadastrar lote. Verifique os campos informados.")
    else:
        form = LoteAnimaisForm()
    return render(request, 'estoque/lote_form.html', {'form': form, 'titulo': 'Novo Lote de Animais'})


def lote_editar(request, pk):
    """Edição de lote de animais (ECC, pasto, cabeças, suplementação)."""
    from .forms import LoteAnimaisForm
    lote = get_object_or_404(LoteAnimais, pk=pk)
    if request.method == 'POST':
        form = LoteAnimaisForm(request.POST, instance=lote)
        if form.is_valid():
            lote = form.save()
            messages.success(request, f"Lote '{lote.nome}' atualizado. Alertas sincronizados.")
            return redirect('estoque:painel')
        messages.error(request, "Erro ao atualizar o lote. Verifique os dados.")
    else:
        form = LoteAnimaisForm(instance=lote)
    return render(request, 'estoque/lote_form.html', {'form': form, 'lote': lote, 'titulo': f'Editar {lote.nome}'})


def lote_excluir(request, pk):
    """Desativação segura (soft delete) de lote de animais."""
    lote = get_object_or_404(LoteAnimais, pk=pk)
    if request.method == 'POST':
        nome = lote.nome
        lote.ativo = False
        lote.save()
        messages.success(request, f"Lote '{nome}' desativado com sucesso.")
        return redirect('estoque:painel')
    return redirect('estoque:painel')


# ---------------------------------------------------------------------------
# Demonstração — Dados Fictícios para AgroHack
# ---------------------------------------------------------------------------

def carregar_demonstracao(request):
    """
    Carrega base de dados fictícios claramente marcados como demonstração.
    Dados NÃO são apresentados como oficiais (RN04, guia §2 §7).
    """
    from .seed import popular_dados_demonstracao
    total = popular_dados_demonstracao()
    messages.success(
        request,
        f"Base de demonstração do AgroHack carregada: {total} registro(s) processado(s). "
        f"[ATENÇÃO: dados fictícios para fins de demonstração — não representam base oficial.]"
    )
    return redirect('estoque:painel')
