from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import date
from decimal import Decimal
import json

from .models import Produto, Lote, Movimentacao, LoteAnimais
from .analises import (
    gerar_alertas_priorizados,
    estimar_duracao,
    acompanhamento_temporal,
    calcular_estoque_critico,
    analisar_validade
)


def painel(request):
    """
    Visão consolidada do Sistema AGROGADO (RF02.1, RF02.2, RF02.3):
    - Métricas Principais e Cotações Regionais (Ariquemes / RO)
    - To-Do List Rural Semafórica (🔴 Crítico, 🟡 Atenção, 🟢 Normal)
    - Gestão de Lotes de Gado (LoteAnimais)
    - Estoque de Insumos (Sanidade, Nutrição, Manejo)
    - Simulação Sazonal ("Simular Início da Seca")
    """
    modo_seca = request.GET.get('seca') in ['1', 'true', 'sim']
    fator_seca = Decimal('2.0') if modo_seca else Decimal('1.0')

    # Alertas Priorizados com motor analítico semafórico
    alertas = gerar_alertas_priorizados(modo_seca=modo_seca)

    # 1. Gestão de Lotes de Gado (LoteAnimais)
    lotes_qs = LoteAnimais.objects.filter(ativo=True)
    lotes_formatados = []
    total_cabecas = 0
    total_consumo_diario_sal_kg = Decimal('0.00')
    peso_total_rebanho = Decimal('0.00')

    for lote in lotes_qs:
        total_cabecas += lote.quantidade_cabecas
        consumo_diario_lote_kg = lote.consumo_diario_total_kg * fator_seca
        total_consumo_diario_sal_kg += consumo_diario_lote_kg

        peso_medio = lote.peso_medio_estimado or Decimal('350.00')
        peso_total_rebanho += (peso_medio * Decimal(str(lote.quantidade_cabecas)))

        duracao_dias = lote.duracao_estimada_insumo(fator_seca=fator_seca)

        # Status semafórico da suplementação para este lote
        if duracao_dias is None:
            status_lote = 'SEM_VINCULO'
            status_cor = 'cinza'
        elif duracao_dias <= 7:
            status_lote = 'CRITICO'
            status_cor = 'vermelho'
        elif duracao_dias <= 15:
            status_lote = 'ATENCAO'
            status_cor = 'amarelo'
        else:
            status_lote = 'NORMAL'
            status_cor = 'verde'

        # Escore corporal (ECC 1-5)
        ecc_val = float(lote.escore_corporal)
        ecc_percent = min(100, max(10, int((ecc_val / 5.0) * 100)))
        if ecc_val < 3.0:
            ecc_class = 'baixo'
            ecc_texto = 'Abaixo do Ideal'
        elif ecc_val <= 4.0:
            ecc_class = 'ideal'
            ecc_texto = 'Ideal / Bom'
        else:
            ecc_class = 'alto'
            ecc_texto = 'Sobrepeso'

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
            'peso_medio_estimado': lote.peso_medio_estimado,
            'consumo_diario_cabeca_g': int(lote.consumo_diario_cabeca * 1000 * fator_seca),
            'consumo_diario_total_kg': consumo_diario_lote_kg,
            'insumo_nome': lote.insumo_suplementar.nome if lote.insumo_suplementar else 'Nenhum vinculado',
            'insumo_id': lote.insumo_suplementar.id if lote.insumo_suplementar else None,
            'duracao_dias': duracao_dias,
            'status_lote': status_lote,
            'status_cor': status_cor,
            'observacoes': lote.observacoes,
        })

    # Cotação Regional da @ Boi Gordo (Ariquemes / Rondônia)
    cotacao_arroba = Decimal('228.50')
    # Conversão de peso vivo para carcaça (rendimento aproximado de 50%, @ = 15kg carcaça = 30kg peso vivo)
    arrobas_totais = (peso_total_rebanho / Decimal('30.00')) if total_cabecas > 0 else Decimal('0.00')
    patrimonio_rebanho = arrobas_totais * cotacao_arroba

    # 2. Produtos e Estoque de Insumos (Insumo)
    produtos_qs = Produto.objects.filter(ativo=True)
    total_produtos = produtos_qs.count()
    valor_total_estocado = Decimal('0.00')
    produtos_insumos = []

    hoje = date.today()

    for p in produtos_qs:
        saldo = p.saldo_atual
        minimo = p.estoque_minimo
        valor_item = p.valor_total_estoque or Decimal('0.00')
        valor_total_estocado += valor_item

        # Agrupamento das categorias para a interface de fazenda
        if p.categoria in ['MEDICAMENTOS']:
            grupo_categoria = 'Sanidade'
            grupo_classe = 'sanidade'
        elif p.categoria in ['SUPLEMENTOS']:
            grupo_categoria = 'Nutrição'
            grupo_classe = 'nutricao'
        else:
            grupo_categoria = 'Manejo'
            grupo_classe = 'manejo'

        # Status Semafórico
        if saldo <= 0 or (minimo is not None and saldo <= minimo):
            status_estoque = 'CRITICO'
            status_cor = 'vermelho'
        elif minimo is not None and saldo <= (minimo * Decimal('1.5')):
            status_estoque = 'ATENCAO'
            status_cor = 'amarelo'
        else:
            status_estoque = 'NORMAL'
            status_cor = 'verde'

        # Próxima Validade
        lote_proximo = p.lotes.filter(data_validade__isnull=False).order_by('data_validade').first()
        validade_data = lote_proximo.data_validade if lote_proximo else None
        dias_validade = (validade_data - hoje).days if validade_data else None

        # Cobertura do estoque
        duracao = estimar_duracao(p)

        # Percentual de nível em relação ao mínimo
        if minimo and minimo > 0:
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
            'preco_unitario': p.preco_referencia,
            'valor_total': valor_item,
            'validade': validade_data,
            'dias_validade': dias_validade,
            'cobertura_dias': duracao.get('dias'),
        })

    # Contadores de Semáforo
    alta_prioridade = sum(1 for a in alertas if a['prioridade'] == 'ALTA')
    media_prioridade = sum(1 for a in alertas if a['prioridade'] == 'MEDIA')
    baixa_prioridade = sum(1 for a in alertas if a['prioridade'] == 'BAIXA')

    context = {
        'alertas': alertas,
        'lotes_animais': lotes_formatados,
        'produtos_insumos': produtos_insumos,
        'modo_seca': modo_seca,
        'kpis': {
            'alta_prioridade': alta_prioridade,
            'media_prioridade': media_prioridade,
            'baixa_prioridade': baixa_prioridade,
            'itens_regulares': baixa_prioridade,
            'total_produtos': total_produtos,
            'total_cabecas': total_cabecas,
            'total_lotes': len(lotes_formatados),
            'total_consumo_diario_sal_kg': total_consumo_diario_sal_kg,
            'valor_total_estocado': valor_total_estocado,
            'cotacao_arroba': cotacao_arroba,
            'patrimonio_rebanho': patrimonio_rebanho,
            'arrobas_totais': arrobas_totais,
        },
        'total_alertas_urgentes': alta_prioridade,
    }
    return render(request, 'estoque/painel.html', context)


def produto_lista(request):
    """
    Consulta organizada de insumos, saldos e situação de estoque.
    """
    busca = request.GET.get('busca', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    status = request.GET.get('status', '').strip()

    qs = Produto.objects.filter(ativo=True)
    if busca:
        qs = qs.filter(nome__icontains=busca)
    if categoria:
        qs = qs.filter(categoria=categoria)

    produtos_formatados = []
    for p in qs:
        saldo = p.saldo_atual
        minimo = p.estoque_minimo

        if minimo is not None and saldo <= minimo:
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
            'categoria': p.get_categoria_display(),
            'unidade': p.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'status_estoque': status_estoque,
            'cobertura_dias': duracao['dias'],
            'preco_unitario': p.preco_referencia,
            'valor_total': p.valor_total_estoque,
        })

    categorias_disponiveis = [c[0] for c in Produto.CATEGORIAS]

    context = {
        'produtos': produtos_formatados,
        'categorias': categorias_disponiveis,
        'busca_atual': busca,
        'categoria_selecionada': categoria,
        'status_selecionado': status,
    }
    return render(request, 'estoque/produto_lista.html', context)


def produto_detalhe(request, pk):
    """
    Ficha detalhada de insumo, lotes, histórico e metodologia de cálculo.
    """
    p = get_object_or_404(Produto, pk=pk)
    saldo = p.saldo_atual
    minimo = p.estoque_minimo

    if minimo is not None and saldo <= minimo:
        status_estoque = 'CRITICO'
    elif minimo is not None and saldo <= (minimo * Decimal('1.5')):
        status_estoque = 'ATENCAO'
    else:
        status_estoque = 'NORMAL'

    duracao = estimar_duracao(p)
    hoje = date.today()

    lotes_qs = p.lotes.all()
    lotes_formatados = []
    proxima_validade = None
    menor_dias_validade = None

    for l in lotes_qs:
        dias = (l.data_validade - hoje).days if l.data_validade else None
        vencido = (dias is not None and dias < 0)
        proximo = (dias is not None and 0 <= dias <= 30)

        if l.data_validade:
            if menor_dias_validade is None or dias < menor_dias_validade:
                menor_dias_validade = dias
                proxima_validade = l.data_validade

        lotes_formatados.append({
            'numero': l.numero_lote,
            'data_validade': l.data_validade,
            'quantidade': l.saldo_lote,
            'vencido': vencido,
            'proximo_vencimento': proximo,
        })

    # Alertas específicos deste produto
    todos_alertas = gerar_alertas_priorizados()
    alertas_produto = [a for a in todos_alertas if a['produto_id'] == p.id]

    # Movimentações recentes
    movs = p.movimentacoes.all()[:30]

    context = {
        'produto': {
            'id': p.id,
            'nome': p.nome,
            'categoria': p.get_categoria_display(),
            'unidade': p.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'status_estoque': status_estoque,
            'cobertura_dias': duracao['dias'],
            'consumo_medio_diario': duracao['consumo_diario'],
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
            }
            for m in movs
        ],
    }
    return render(request, 'estoque/produto_detalhe.html', context)


def consumo(request):
    """
    Acompanhamento temporal interativo de consumo com Chart.js (RF03.6).
    """
    produtos = Produto.objects.filter(ativo=True)
    produto_id = request.GET.get('produto_id')

    produto_selecionado = None
    if produto_id:
        produto_selecionado = produtos.filter(id=produto_id).first()
    if not produto_selecionado and produtos.exists():
        produto_selecionado = produtos.first()

    chart_labels = []
    chart_data = []
    dados_temporais = []

    if produto_selecionado:
        dados = acompanhamento_temporal(produto_selecionado)
        chart_labels = dados['labels']
        chart_data = dados['valores']
        dados_temporais = dados['dados_tabela']

    context = {
        'lista_produtos': [{'id': p.id, 'nome': p.nome, 'unidade': p.unidade} for p in produtos],
        'produto_selecionado': {
            'id': produto_selecionado.id if produto_selecionado else None,
            'nome': produto_selecionado.nome if produto_selecionado else '',
            'unidade': produto_selecionado.unidade if produto_selecionado else '',
            'saldo': produto_selecionado.saldo_atual if produto_selecionado else 0,
        } if produto_selecionado else None,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'dados_temporais': dados_temporais,
    }
    return render(request, 'estoque/consumo.html', context)


def consumo_produto(request, pk):
    return redirect(f"/consumo/?produto_id={pk}")


def mapear_categoria(texto):
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


def normalizar_data(texto):
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
            d = date(int(partes[2]), int(partes[1]), int(partes[0]))
            return d.isoformat()
    except (ValueError, IndexError, TypeError):
        pass
    return None


def importar(request):
    """
    Carga e Ingestão de Registros de Estoque com suporte aos 13 campos (RF01.1, RF01.2).
    Gera prévia detalhada com validação de linha a linha, RN01 e RN02.
    """
    previa_importacao = None

    if request.method == 'POST' and request.FILES.get('arquivo_csv'):
        arquivo = request.FILES['arquivo_csv']
        nome_arquivo = arquivo.name.lower()

        if not nome_arquivo.endswith('.csv'):
            messages.error(request, "Formato inválido. Por favor, envie um arquivo com extensão .csv.")
            return render(request, 'estoque/importar.html', {'previa_importacao': None})

        # Decodificação com fallback para UTF-8-sig e Latin-1
        conteudo_raw = arquivo.read()
        texto_csv = None
        for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                texto_csv = conteudo_raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not texto_csv:
            messages.error(request, "Não foi possível decodificar o arquivo. Verifique a codificação UTF-8.")
            return render(request, 'estoque/importar.html', {'previa_importacao': None})

        # Detecção de delimitador (, ou ;)
        primeira_linha = texto_csv.splitlines()[0] if texto_csv.splitlines() else ''
        delimitador = ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','

        import csv
        import io
        leitor = csv.DictReader(io.StringIO(texto_csv), delimiter=delimitador)

        linhas_previa = []
        linhas_validas_para_sessao = []
        erros_gerais = []

        # Mapa de normalização dos 13 campos oficiais do regulamento
        mapa_campos = {
            'produto': ['produto', 'nome', 'insumo', 'item'],
            'categoria': ['categoria', 'tipo_produto', 'setor'],
            'unidade': ['unidade', 'un', 'und', 'unidade_medida'],
            'quantidade': ['quantidade', 'qtd', 'volume', 'quant'],
            'estoque_minimo': ['estoque_minimo', 'minimo', 'est_min', 'estoque_min'],
            'tipo_movimentacao': ['tipo_movimentacao', 'tipo', 'operacao', 'movimentacao'],
            'data_movimentacao': ['data_movimentacao', 'data', 'dt_mov', 'data_mov'],
            'preco_aquisicao': ['preco_aquisicao', 'preco_unitario', 'preco', 'custo', 'valor_unitario'],
            'lote': ['lote', 'num_lote', 'numero_lote'],
            'data_validade': ['data_validade', 'validade', 'dt_val', 'vencimento'],
            'fornecedor': ['fornecedor', 'empresa', 'origem'],
            'destino': ['destino', 'setor_destino', 'talhao', 'pasto', 'lote_animal'],
            'responsavel': ['responsavel', 'operador', 'colaborador', 'usuario'],
        }

        # Cache de produtos existentes para validação RN01 (não misturar unidades)
        produtos_existentes = {p.nome.lower().strip(): p for p in Produto.objects.all()}

        num_linha = 1
        for row in leitor:
            num_linha += 1
            # Normalizar chaves do dicionário para minúsculas sem espaços
            row_clean = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items() if k}

            def obter_campo(chave_padrao):
                for alias in mapa_campos.get(chave_padrao, []):
                    if alias in row_clean and row_clean[alias] != '':
                        return row_clean[alias]
                return ''

            produto_nome = obter_campo('produto')
            categoria_str = obter_campo('categoria')
            unidade_str = obter_campo('unidade')
            qtd_str = obter_campo('quantidade')
            tipo_mov = obter_campo('tipo_movimentacao').upper()
            data_mov_str = obter_campo('data_movimentacao')
            est_min_str = obter_campo('estoque_minimo')
            preco_str = obter_campo('preco_aquisicao')
            lote_str = obter_campo('lote')
            validade_str = obter_campo('data_validade')
            fornecedor_str = obter_campo('fornecedor')
            destino_str = obter_campo('destino')
            responsavel_str = obter_campo('responsavel')

            valido = True
            motivo_invalido = ""

            # Validações obrigatórias
            if not produto_nome:
                valido = False
                motivo_invalido = "Nome do produto não informado"
            elif not unidade_str:
                valido = False
                motivo_invalido = "Unidade de medida não informada"
            else:
                # RN01: Verificar conflito de unidades para produtos já cadastrados
                p_exist = produtos_existentes.get(produto_nome.lower())
                if p_exist and p_exist.unidade.lower() != unidade_str.lower():
                    valido = False
                    motivo_invalido = f"Conflito de unidade (RN01): Produto já cadastrado em '{p_exist.unidade}'"

            # Validação do tipo de movimentação
            if tipo_mov in ['ENTRADA', 'E', 'IN', 'COMPRA']:
                tipo_mov = 'ENTRADA'
            elif tipo_mov in ['SAIDA', 'SAÍDA', 'S', 'OUT', 'CONSUMO', 'APLICACAO']:
                tipo_mov = 'SAIDA'
            else:
                valido = False
                motivo_invalido = f"Tipo de movimentação inválido ('{tipo_mov}')"

            # Validação da quantidade
            qtd_decimal = None
            try:
                qtd_limpa = qtd_str.replace('.', '').replace(',', '.') if (',' in qtd_str and '.' in qtd_str) else qtd_str.replace(',', '.')
                qtd_decimal = Decimal(qtd_limpa)
                if qtd_decimal <= 0:
                    valido = False
                    motivo_invalido = "Quantidade deve ser maior que zero"
            except Exception:
                valido = False
                motivo_invalido = f"Quantidade numérica inválida ('{qtd_str}')"

            # Parse de campos opcionais com preservação estrita de ausentes (RN02)
            est_min_dec = None
            if est_min_str:
                try:
                    est_min_dec = str(Decimal(est_min_str.replace(',', '.')))
                except Exception:
                    pass

            preco_dec = None
            if preco_str:
                try:
                    preco_dec = str(Decimal(preco_str.replace(',', '.')))
                except Exception:
                    pass

            data_mov_norm = normalizar_data(data_mov_str) or date.today().isoformat()
            validade_norm = normalizar_data(validade_str)

            linha_dict = {
                'linha_num': num_linha,
                'produto': produto_nome,
                'categoria': categoria_str or 'Geral',
                'categoria_codigo': mapear_categoria(categoria_str),
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
                linhas_validas_para_sessao.append(linha_dict)
            else:
                erros_gerais.append(f"Linha {num_linha} ({produto_nome or 'Item'}): {motivo_invalido}")

        request.session['previa_importacao_linhas'] = linhas_validas_para_sessao

        previa_importacao = {
            'total_linhas': len(linhas_previa),
            'erros': erros_gerais[:10],
            'linhas': linhas_previa[:50],  # Prévia das primeiras 50 linhas
            'total_validas': len(linhas_validas_para_sessao)
        }

    return render(request, 'estoque/importar.html', {'previa_importacao': previa_importacao})


def confirmar_importacao(request):
    """
    Gravação atômica dos registros pré-validados na importação CSV (RF01.1, RF01.3).
    """
    if request.method == 'POST':
        linhas = request.session.get('previa_importacao_linhas', [])
        if not linhas:
            messages.warning(request, "Nenhum registro pendente para gravação. Selecione um arquivo CSV novamente.")
            return redirect('estoque:importar')

        from django.db import transaction
        total_movs_criadas = 0

        with transaction.atomic():
            for l in linhas:
                # 1. Obter ou criar Produto
                produto, criado = Produto.objects.get_or_create(
                    nome=l['produto'],
                    defaults={
                        'categoria': l['categoria_codigo'],
                        'unidade': l['unidade'],
                        'estoque_minimo': Decimal(l['estoque_minimo']) if l.get('estoque_minimo') else None,
                        'preco_referencia': Decimal(l['preco_aquisicao']) if l.get('preco_aquisicao') else None,
                    }
                )

                # Atualiza estoque mínimo ou preço de referência se antes não existia
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

                # 2. Obter ou criar Lote se informado
                lote = None
                if l.get('lote'):
                    data_val = date.fromisoformat(l['data_validade']) if l.get('data_validade') else None
                    lote, _ = Lote.objects.get_or_create(
                        produto=produto,
                        numero_lote=l['lote'],
                        defaults={'data_validade': data_val}
                    )
                    if data_val and not lote.data_validade:
                        lote.data_validade = data_val
                        lote.save()

                # 3. Criar Movimentação
                data_mov = date.fromisoformat(l['data_movimentacao']) if l.get('data_movimentacao') else date.today()
                preco_unit = Decimal(l['preco_aquisicao']) if l.get('preco_aquisicao') else None

                Movimentacao.objects.create(
                    produto=produto,
                    lote=lote,
                    tipo=l['tipo_movimentacao'],
                    quantidade=Decimal(l['quantidade']),
                    data_movimentacao=data_mov,
                    preco_unitario=preco_unit,
                    fornecedor=l.get('fornecedor', ''),
                    destino=l.get('destino', ''),
                    responsavel=l.get('responsavel', '')
                )
                total_movs_criadas += 1

        # Limpar sessão após gravação segura
        if 'previa_importacao_linhas' in request.session:
            del request.session['previa_importacao_linhas']

        messages.success(
            request,
            f"Importação concluída com sucesso! {total_movs_criadas} registros foram gravados. "
            f"O motor analítico recalculou todos os diagnósticos e pendências em tempo real (RF01.3)."
        )
        return redirect('estoque:painel')

    return redirect('estoque:importar')


def carregar_demonstracao(request):
    """
    Carrega dados simulados de demonstração para avaliação do AgroHack.
    """
    from .seed import popular_dados_demonstracao
    total = popular_dados_demonstracao()
    messages.success(request, f"Base de demonstração do AgroHack carregada com sucesso! {total} registros foram processados e reanalisados.")
    return redirect('estoque:painel')


def movimentacao_nova(request):
    """
    Registro manual de movimentação para demonstração de reanálise automática (RF01.3)
    com validação estrita de bloqueio de saldo negativo (RN01.1).
    """
    produtos = Produto.objects.filter(ativo=True)

    if request.method == 'POST':
        produto_id = request.POST.get('produto')
        tipo = request.POST.get('tipo')
        quantidade_str = request.POST.get('quantidade', '').strip()
        data_str = request.POST.get('data')
        lote_num = request.POST.get('lote', '').strip()
        validade_str = request.POST.get('validade', '').strip()
        preco_str = request.POST.get('preco_unitario', '').strip()
        destino = request.POST.get('destino', '').strip()
        responsavel = request.POST.get('responsavel', '').strip()
        fornecedor = request.POST.get('fornecedor', '').strip()

        produto = get_object_or_404(Produto, id=produto_id)

        try:
            quantidade = Decimal(quantidade_str)
            if quantidade <= Decimal('0.00'):
                raise ValueError("A quantidade deve ser maior que zero.")
        except Exception:
            messages.error(request, "Quantidade informada é inválida. Utilize um valor numérico positivo.")
            return render(request, 'estoque/movimentacao_form.html', {
                'produtos': [{'id': p.id, 'nome': p.nome, 'unidade': p.unidade, 'saldo': p.saldo_atual} for p in produtos],
                'produto_selecionado_id': int(produto_id),
                'data_padrao': data_str or date.today().isoformat(),
            })

        # RN01.1 - Bloqueio de Saldo Negativo
        if tipo == 'SAIDA':
            saldo_atual = produto.saldo_atual
            if quantidade > saldo_atual:
                messages.error(
                    request,
                    f"Operação não permitida (RN01.1): A quantidade solicitada ({quantidade} {produto.unidade}) "
                    f"é superior ao saldo atual disponível em estoque ({saldo_atual} {produto.unidade}). "
                    f"A saída não foi registrada para evitar saldo negativo."
                )
                return render(request, 'estoque/movimentacao_form.html', {
                    'produtos': [{'id': p.id, 'nome': p.nome, 'unidade': p.unidade, 'saldo': p.saldo_atual} for p in produtos],
                    'produto_selecionado_id': int(produto_id),
                    'data_padrao': data_str or date.today().isoformat(),
                })

        lote = None
        if lote_num:
            data_val = date.fromisoformat(validade_str) if validade_str else None
            lote, _ = Lote.objects.get_or_create(
                produto=produto,
                numero_lote=lote_num,
                defaults={'data_validade': data_val}
            )
            if data_val and not lote.data_validade:
                lote.data_validade = data_val
                lote.save()

        preco = Decimal(preco_str) if preco_str else None

        Movimentacao.objects.create(
            produto=produto,
            lote=lote,
            tipo=tipo,
            quantidade=quantidade,
            data_movimentacao=date.fromisoformat(data_str) if data_str else timezone.now().date(),
            preco_unitario=preco,
            destino=destino,
            responsavel=responsavel,
            fornecedor=fornecedor
        )

        messages.success(
            request,
            f"Movimentação de {tipo.lower()} ({quantidade} {produto.unidade}) registrada com sucesso! "
            f"Todas as análises e o painel de pendências foram reprocessados automaticamente (RF01.3)."
        )
        return redirect('estoque:painel')

    context = {
        'produtos': [
            {'id': p.id, 'nome': p.nome, 'unidade': p.unidade, 'saldo': p.saldo_atual}
            for p in produtos
        ],
        'produto_selecionado_id': int(request.GET.get('produto_id', 0)) if request.GET.get('produto_id') else '',
        'data_padrao': date.today().isoformat(),
    }
    return render(request, 'estoque/movimentacao_form.html', context)


def lote_novo(request):
    """
    Cadastro amigável de novo lote de animais (LoteAnimais).
    """
    from .forms import LoteAnimaisForm
    if request.method == 'POST':
        form = LoteAnimaisForm(request.POST)
        if form.is_valid():
            lote = form.save()
            messages.success(
                request,
                f"Lote '{lote.nome}' ({lote.quantidade_cabecas} cabeças) cadastrado com sucesso! "
                f"As demandas de suplementação e o motor de alertas foram recalculados."
            )
            return redirect('estoque:painel')
        else:
            messages.error(request, "Erro ao cadastrar lote. Verifique os campos informados.")
    else:
        form = LoteAnimaisForm()

    return render(request, 'estoque/lote_form.html', {'form': form, 'titulo': 'Novo Lote de Animais'})


def lote_editar(request, pk):
    """
    Edição rápida de lote de animais (troca de pasto, atualização de cabeças ou ECC).
    """
    from .forms import LoteAnimaisForm
    lote = get_object_or_404(LoteAnimais, pk=pk)

    if request.method == 'POST':
        form = LoteAnimaisForm(request.POST, instance=lote)
        if form.is_valid():
            lote = form.save()
            messages.success(
                request,
                f"Lote '{lote.nome}' atualizado com sucesso! Manejo e alertas foram sincronizados."
            )
            return redirect('estoque:painel')
        else:
            messages.error(request, "Erro ao atualizar o lote. Verifique os dados.")
    else:
        form = LoteAnimaisForm(instance=lote)

    return render(request, 'estoque/lote_form.html', {'form': form, 'lote': lote, 'titulo': f'Editar {lote.nome}'})


def lote_excluir(request, pk):
    """
    Desativação segura de lote de animais.
    """
    lote = get_object_or_404(LoteAnimais, pk=pk)
    if request.method == 'POST':
        nome = lote.nome
        lote.ativo = False
        lote.save()
        messages.success(request, f"Lote '{nome}' desativado com sucesso.")
        return redirect('estoque:painel')

    return redirect('estoque:painel')

