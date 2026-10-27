"""
analises.py — Motor Analítico Determinístico do AGROGADO
AgroHack 2026/2 — IFRO Campus Ariquemes

Implementação estrita e auditável das regras de negócio (RF03.1 a RF03.7,
RF02.1 a RF02.3, RN01 a RN04) sem caixa-preta de IA (RN04).

Fórmulas implementadas (documento especificacao_do_projeto v3.0):
  §6.1 — Saldo Atual do Insumo (no ORM, propriedade Produto.saldo_atual)
  §6.2 — Consumo Diário Global do Rebanho por Insumo
  §6.3 — Autonomia de Estoque em Dias (⌊ Saldo / Consumo Diário ⌋)
  §6.4 — Projeção de Perda por Validade (sobra estimada a descartar)
  §6.5 — Detecção de Saídas Atípicas (μ + 2σ, N ≥ 5)

Todas as funções:
  - Recebem tipos explícitos (type hints) e documentam campos usados
  - Comunicam incerteza em linguagem natural quando dados são insuficientes (RN03)
  - Preservam None para dados ausentes, nunca convertem ausência em zero (RN02)
  - Retornam justificativa explicável em português para cada alerta (RF02.3)
  - São testáveis unitariamente e determinísticas (sem randomização ou ML)
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from django.db.models import Sum

from .models import (
    CampanhaVacina,
    Lote,
    LoteAnimais,
    Movimentacao,
    Produto,
)

# Tipo estruturado de alerta para o Dashboard To-Do List
AlertaDict = dict[str, Any]

# ---------------------------------------------------------------------------
# §6.3 — Estimativa de Duração de Estoque por Consumo Histórico
# ---------------------------------------------------------------------------

def estimar_duracao(produto: Produto, janela_dias: int = 30) -> dict[str, Any]:
    """
    RF03.3 / §6.3 — Estima a cobertura restante do estoque (dias) a partir
    do consumo médio diário observado na janela móvel de `janela_dias` dias.

    Condições mínimas para calcular (RN03):
      - Saldo atual > 0
      - Pelo menos 2 saídas registradas na janela (caso contrário: "Não estimado")

    Args:
        produto: instância de Produto com movimentações acessíveis via ORM.
        janela_dias: tamanho da janela histórica em dias (padrão: 30 dias).

    Returns:
        dict com chaves:
          - dias (int | None): dias de cobertura estimados. None = não estimado.
          - consumo_diario (Decimal | None): consumo médio diário calculado.
          - justificativa (str): explicação em linguagem natural (RF02.3).
          - estimado (bool): True se há dados suficientes para o cálculo.
    """
    saldo = produto.saldo_atual

    if saldo <= Decimal('0.00'):
        return {
            'dias': 0,
            'consumo_diario': Decimal('0.00'),
            'justificativa': 'Saldo zerado ou negativo — reposição imediata necessária.',
            'estimado': True,
        }

    hoje = date.today()
    data_limite = hoje - timedelta(days=janela_dias)

    saidas_qs = produto.movimentacoes.filter(
        tipo='SAIDA',
        data_movimentacao__gte=data_limite,
    )
    qtd_saidas = saidas_qs.count()

    # RN03: mínimo de 2 saídas para calcular taxa de consumo
    if qtd_saidas < 2:
        return {
            'dias': None,
            'consumo_diario': None,
            'justificativa': (
                f'Não estimado: histórico insuficiente de movimentações — '
                f'apenas {qtd_saidas} saída(s) registrada(s) nos últimos {janela_dias} dias '
                f'(mínimo: 2 registros para calcular consumo médio).'
            ),
            'estimado': False,
        }

    total_saidas = saidas_qs.aggregate(total=Sum('quantidade'))['total'] or Decimal('0.00')
    if total_saidas <= Decimal('0.00'):
        return {
            'dias': None,
            'consumo_diario': Decimal('0.00'),
            'justificativa': f'Não estimado: saídas registradas totalizam zero na janela de {janela_dias} dias.',
            'estimado': False,
        }

    consumo_diario = total_saidas / Decimal(str(janela_dias))
    # §6.3: ⌈ Saldo / Consumo Diário ⌉ — teto (especificacao_de_requisitos.md §6.3)
    dias_estimados = math.ceil(float(saldo / consumo_diario))

    return {
        'dias': dias_estimados,
        'consumo_diario': consumo_diario,
        'justificativa': (
            f'Consumo médio de {consumo_diario:.3f} {produto.unidade}/dia '
            f'nos últimos {janela_dias} dias ({qtd_saidas} saídas registradas).'
        ),
        'estimado': True,
    }


# ---------------------------------------------------------------------------
# §6.2 — Consumo Diário Global do Rebanho por Insumo
# ---------------------------------------------------------------------------

def calcular_consumo_diario_global(produto: Produto, fator_seca: Decimal = Decimal('1.0')) -> dict[str, Any]:
    """
    RF03.3 / §6.2 — Calcula o Consumo Diário Global de um insumo cruzando
    todos os lotes de animais ativos que têm este produto como insumo suplementar.

    Fórmula §6.2:
      Consumo Diário Global = Σᵢ (Cabeças do Lotᵢ × Consumo Diário por Cabeçaᵢ) × fator_seca

    Args:
        produto: Produto a ser analisado.
        fator_seca: multiplicador de consumo sazonal (1.0 = águas; 2.0 = seca).

    Returns:
        dict com:
          - consumo_total_kg_dia (Decimal): consumo diário global em kg/dia.
          - lotes_vinculados (list[dict]): detalhamento por lote.
          - total_cabecas (int): total de cabeças consumindo este insumo.
          - tem_rebanho_vinculado (bool): True se há pelo menos 1 lote ativo vinculado.
    """
    lotes = LoteAnimais.objects.filter(
        insumo_suplementar=produto,
        ativo=True,
        quantidade_cabecas__gt=0,
    )

    consumo_total = Decimal('0.00')
    total_cabecas = 0
    lotes_detalhados = []

    for lote in lotes:
        consumo_lote = lote.consumo_diario_total_kg * fator_seca
        consumo_total += consumo_lote
        total_cabecas += lote.quantidade_cabecas
        lotes_detalhados.append({
            'lote_id': lote.id,
            'lote_nome': lote.nome,
            'cabecas': lote.quantidade_cabecas,
            'consumo_cabeca_kg': lote.consumo_diario_cabeca,
            'consumo_lote_kg': consumo_lote,
            'pasto': lote.pasto_localizacao,
        })

    return {
        'consumo_total_kg_dia': consumo_total,
        'lotes_vinculados': lotes_detalhados,
        'total_cabecas': total_cabecas,
        'tem_rebanho_vinculado': len(lotes_detalhados) > 0,
    }


def autonomia_por_rebanho(produto: Produto, fator_seca: Decimal = Decimal('1.0')) -> dict[str, Any]:
    """
    RF03.3 / §6.3 — Autonomia de Estoque em Dias calculada pelo Consumo Diário Global.
    Usa a fórmula §6.2 para o consumo e §6.3 (floor) para a autonomia.

    Este método complementa `estimar_duracao()` que usa o histórico de saídas.
    Quando há rebanho vinculado, usa o consumo zootécnico do lote (mais preciso);
    caso contrário, delega para o histórico de saídas.

    Returns:
        dict com chaves: dias, consumo_diario, justificativa, estimado, fonte.
    """
    saldo = produto.saldo_atual
    if saldo <= Decimal('0.00'):
        return {
            'dias': 0,
            'consumo_diario': Decimal('0.00'),
            'justificativa': 'Saldo zerado ou negativo.',
            'estimado': True,
            'fonte': 'saldo_zero',
        }

    dados_rebanho = calcular_consumo_diario_global(produto, fator_seca)

    if not dados_rebanho['tem_rebanho_vinculado']:
        # Fallback para estimativa histórica (especificação §6.3)
        resultado = estimar_duracao(produto)
        resultado['fonte'] = 'historico_saidas'
        return resultado

    consumo_dia = dados_rebanho['consumo_total_kg_dia']
    if consumo_dia <= Decimal('0.00'):
        return {
            'dias': None,
            'consumo_diario': Decimal('0.00'),
            'justificativa': 'Não estimado: consumo diário do rebanho calculado como zero.',
            'estimado': False,
            'fonte': 'rebanho_zero',
        }

    # Normaliza saldo para kg se necessário
    unidade = produto.unidade.lower()
    saldo_kg = saldo
    if 'sc' in unidade or 'saco' in unidade:
        saldo_kg = saldo * Decimal('30.0')

    # §6.3: ⌊ Saldo / Consumo Diário Global ⌋ — floor conforme especificação v3.0
    dias_estimados = math.floor(float(saldo_kg / consumo_dia))
    cabecas = dados_rebanho['total_cabecas']
    lotes_nomes = ', '.join(d['lote_nome'] for d in dados_rebanho['lotes_vinculados'])

    return {
        'dias': dias_estimados,
        'consumo_diario': consumo_dia,
        'justificativa': (
            f'Consumo diário do rebanho: {consumo_dia:.3f} kg/dia '
            f'({cabecas} cabeças em {len(dados_rebanho["lotes_vinculados"])} lote(s): {lotes_nomes})'
            f'{" — [Simulação Seca: consumo acelerado]" if fator_seca > Decimal("1.0") else ""}.'
        ),
        'estimado': True,
        'fonte': 'consumo_rebanho',
    }


# ---------------------------------------------------------------------------
# RF03.1 — Estoque Crítico e Risco de Falta
# ---------------------------------------------------------------------------

def calcular_estoque_critico(produto: Produto) -> Optional[AlertaDict]:
    """
    RF03.1 / §6.2 (priorização) — Identifica produtos com risco de falta.

    Prioridades (especificacao_de_requisitos §6.2):
      🔴 ALTA: saldo <= 0 (esgotado) ou saldo <= estoque_minimo
      🟡 MÉDIA: saldo <= 1.5 × estoque_minimo (zona de atenção)
      (sem alerta se saldo > 1.5 × estoque_minimo)

    Returns:
        AlertaDict ou None se o produto está em situação regular.
    """
    saldo = produto.saldo_atual
    minimo = produto.estoque_minimo

    # Ruptura emergencial — saldo zerado ou negativo
    if saldo <= Decimal('0.00'):
        return {
            'tipo': 'ESTOQUE_CRITICO',
            'tipo_display': 'Estoque Crítico — Esgotado',
            'prioridade': 'ALTA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'justificativa': (
                f"🔴 Estoque esgotado: Saldo atual de {produto.nome} é "
                f"{saldo} {produto.unidade} — zerado ou negativo. "
                f"Reposição imediata necessária para evitar paralisação operacional."
            ),
            'valor_total': Decimal('0.00'),
        }

    if minimo is None:
        # Sem estoque mínimo definido, não há base para comparação (RN02)
        return None

    if saldo <= minimo:
        estimativa = estimar_duracao(produto)
        sufixo_dias = ''
        if estimativa.get('estimado') and estimativa.get('dias') is not None:
            sufixo_dias = f" — estimado para esgotar em ~{estimativa['dias']} dia(s)"

        return {
            'tipo': 'ESTOQUE_CRITICO',
            'tipo_display': 'Estoque Crítico',
            'prioridade': 'ALTA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'justificativa': (
                f"🔴 Estoque crítico de {produto.nome}: Saldo atual ({saldo} {produto.unidade}) "
                f"atingiu o limite mínimo ({minimo} {produto.unidade}){sufixo_dias}. "
                f"Providencie reposição imediatamente."
            ),
            'valor_total': produto.valor_total_estoque,
        }

    if saldo <= (minimo * Decimal('1.5')):
        return {
            'tipo': 'ESTOQUE_ATENCAO',
            'tipo_display': 'Atenção para Reposição',
            'prioridade': 'MEDIA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'justificativa': (
                f"🟡 Atenção: Estoque de {produto.nome} em zona de alerta. "
                f"Saldo atual ({saldo} {produto.unidade}) está entre 100% e 150% "
                f"do mínimo ({minimo} {produto.unidade}). Avalie reposição em breve."
            ),
            'valor_total': produto.valor_total_estoque,
        }

    return None


# ---------------------------------------------------------------------------
# RF03.2 / §6.4 — Análise de Validade e Projeção de Perdas
# ---------------------------------------------------------------------------

def analisar_validade(produto: Produto, dias_alerta: int = 30) -> list[AlertaDict]:
    """
    RF03.2 / §6.4 — Análise de Validade e Risco de Perdas de Insumos.

    Cruza data de validade dos lotes com o ritmo de consumo para estimar
    sobra a ser descartada. Gera alertas diferenciados:

      🔴 ALTA — lote já vencido com saldo restante
      🔴 ALTA — lote vence em <= dias_alerta e haverá sobra estimada (perda financeira)
      🟡 MÉDIA — lote vence em <= dias_alerta sem projeção de consumo disponível

    Fórmula §6.4:
      Sobra Estimada = Saldo do Lote − (Consumo Diário × Dias Restantes)
      Se Dias Restantes ≤ 30 e Sobra > 0 → 🔴 ALTA com valor financeiro em risco.

    Returns:
        Lista de AlertaDict (pode ser vazia se não houver lotes próximos do vencimento).
    """
    hoje = date.today()
    lotes = produto.lotes.filter(data_validade__isnull=False)
    alertas: list[AlertaDict] = []

    for lote in lotes:
        saldo_lote = lote.saldo_lote
        if saldo_lote <= Decimal('0.00'):
            continue  # Lote sem saldo não gera alerta de perda

        dias_restantes = (lote.data_validade - hoje).days

        if dias_restantes < 0:
            # Lote vencido com saldo restante — 🔴 ALTA imediata
            alertas.append({
                'tipo': 'LOTE_VENCIDO',
                'tipo_display': 'Lote Vencido com Saldo',
                'prioridade': 'ALTA',
                'produto_id': produto.id,
                'produto_nome': produto.nome,
                'lote': lote.numero_lote,
                'validade': lote.data_validade,
                'unidade': produto.unidade,
                'saldo': saldo_lote,
                'estoque_minimo': produto.estoque_minimo,
                'justificativa': (
                    f"🔴 Lote {lote.numero_lote} de {produto.nome} vencido há "
                    f"{abs(dias_restantes)} dia(s) com {saldo_lote} {produto.unidade} "
                    f"ainda em estoque. Descarte ou destinação imediata obrigatória."
                ),
                'valor_total': (
                    (saldo_lote * produto.preco_referencia)
                    if produto.preco_referencia else None
                ),
            })
            continue

        if dias_restantes <= dias_alerta:
            # Tenta projetar consumo para avaliar sobra (§6.4)
            estimativa = estimar_duracao(produto)
            consumo_diario = estimativa.get('consumo_diario')

            if consumo_diario and consumo_diario > Decimal('0.00'):
                consumo_projetado = consumo_diario * Decimal(str(dias_restantes))
                if saldo_lote > consumo_projetado:
                    sobra = saldo_lote - consumo_projetado
                    valor_risco = (sobra * produto.preco_referencia) if produto.preco_referencia else None
                    sufixo_valor = (
                        f" (risco financeiro estimado: R$ {valor_risco:,.2f})"
                        if valor_risco else ""
                    )
                    alertas.append({
                        'tipo': 'RISCO_PERDA_VALIDADE',
                        'tipo_display': 'Risco de Perda por Validade',
                        'prioridade': 'ALTA',
                        'produto_id': produto.id,
                        'produto_nome': produto.nome,
                        'lote': lote.numero_lote,
                        'validade': lote.data_validade,
                        'unidade': produto.unidade,
                        'saldo': saldo_lote,
                        'sobra_estimada': sobra,
                        'estoque_minimo': produto.estoque_minimo,
                        'justificativa': (
                            f"🔴 Risco de perda: Lote {lote.numero_lote} de {produto.nome} vence "
                            f"em {dias_restantes} dia(s). No ritmo atual de consumo "
                            f"({consumo_diario:.3f} {produto.unidade}/dia), cerca de "
                            f"{sobra:.2f} {produto.unidade} não será consumido a tempo"
                            f"{sufixo_valor}. Priorize o uso imediato deste lote."
                        ),
                        'valor_total': (
                            (saldo_lote * produto.preco_referencia)
                            if produto.preco_referencia else None
                        ),
                    })
                    continue
                # Saldo será consumido antes do vencimento — sem alerta de perda
                continue

            # Sem histórico suficiente para projetar — alerta MÉDIA (RN03)
            alertas.append({
                'tipo': 'VALIDADE_PROXIMA',
                'tipo_display': 'Validade Próxima',
                'prioridade': 'MEDIA',
                'produto_id': produto.id,
                'produto_nome': produto.nome,
                'lote': lote.numero_lote,
                'validade': lote.data_validade,
                'unidade': produto.unidade,
                'saldo': saldo_lote,
                'estoque_minimo': produto.estoque_minimo,
                'justificativa': (
                    f"🟡 Lote {lote.numero_lote} de {produto.nome} vence em "
                    f"{dias_restantes} dia(s) com {saldo_lote} {produto.unidade} em estoque. "
                    f"Sem histórico de consumo suficiente para projetar perda — "
                    f"priorize o uso deste lote como precaução."
                ),
                'valor_total': (
                    (saldo_lote * produto.preco_referencia)
                    if produto.preco_referencia else None
                ),
            })

    return alertas


# ---------------------------------------------------------------------------
# RF03.4 / §6.5 — Detecção de Saídas Atípicas (Anomalias)
# ---------------------------------------------------------------------------

def detectar_anomalias(produto: Produto) -> Optional[AlertaDict]:
    """
    RF03.4 / §6.5 — Detecção de movimentações com volumes atipicamente elevados.

    Critério documentado (§6.5): Limite Superior = μ + 2σ (desvio-padrão amostral).
    Condição mínima (RN03): N >= 5 saídas históricas registradas.

    Verifica as 3 saídas mais recentes contra o limite superior histórico.

    Returns:
        AlertaDict 🟡 MÉDIA se há saída atípica recente, None caso contrário.
    """
    saidas = produto.movimentacoes.filter(tipo='SAIDA').order_by('-data_movimentacao')
    total = saidas.count()

    if total < 5:
        return None  # RN03: histórico insuficiente para classificar anomalia

    quantidades = [float(m.quantidade) for m in saidas]
    n = len(quantidades)
    media = sum(quantidades) / n
    # Desvio-padrão amostral (N-1 para amostra)
    variancia = sum((x - media) ** 2 for x in quantidades) / (n - 1)
    desvio_padrao = math.sqrt(variancia)

    if desvio_padrao == 0:
        return None  # Todas as saídas são iguais — nenhuma é atípica

    limite_superior = media + (2 * desvio_padrao)

    # Analisa as 3 saídas mais recentes
    saidas_recentes = list(saidas[:3])
    for s in saidas_recentes:
        if float(s.quantidade) > limite_superior:
            return {
                'tipo': 'ANOMALIA_SAIDA',
                'tipo_display': 'Saída Atípica Detectada',
                'prioridade': 'MEDIA',
                'produto_id': produto.id,
                'produto_nome': produto.nome,
                'unidade': produto.unidade,
                'saldo': produto.saldo_atual,
                'estoque_minimo': produto.estoque_minimo,
                'justificativa': (
                    f"🟡 Saída atípica de {produto.nome}: {s.quantidade} {produto.unidade} "
                    f"em {s.data_movimentacao.strftime('%d/%m/%Y')} supera o limite estatístico "
                    f"(μ={media:.1f}, σ={desvio_padrao:.1f}, limite={limite_superior:.1f}) "
                    f"calculado sobre {n} saídas históricas. "
                    f"Destino registrado: '{s.destino or 'Não informado'}'. "
                    f"Verifique se a retirada foi autorizada."
                ),
                'valor_total': produto.valor_total_estoque,
            }

    return None


# ---------------------------------------------------------------------------
# RF03.7 / RF03.5 — Análise Financeira e Excesso de Capital Parado
# ---------------------------------------------------------------------------

def analisar_financeiro(produto: Produto) -> Optional[AlertaDict]:
    """
    RF03.7 — Identifica produtos com alto capital imobilizado em excesso.

    Critério (especificação §RF03.7):
      Valor em estoque > R$ 5.000,00 E saldo >= 3 × estoque_minimo
      → 🟢 BAIXA (monitoramento — não é urgente, mas orienta decisão de compra)

    Returns:
        AlertaDict 🟢 BAIXA ou None.
    """
    valor = produto.valor_total_estoque
    if valor is None or valor < Decimal('5000.00'):
        return None

    if produto.estoque_minimo and produto.saldo_atual >= (produto.estoque_minimo * Decimal('3.0')):
        return {
            'tipo': 'EXCESSO_ESTOQUE',
            'tipo_display': 'Capital Parado / Excesso de Estoque',
            'prioridade': 'BAIXA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': produto.saldo_atual,
            'estoque_minimo': produto.estoque_minimo,
            'justificativa': (
                f"🟢 Capital imobilizado expressivo: {produto.nome} com R$ {valor:,.2f} em estoque "
                f"({produto.saldo_atual} {produto.unidade}) — 3× acima do mínimo "
                f"({produto.estoque_minimo} {produto.unidade}). "
                f"Evite novas compras deste item no curto prazo para proteger o fluxo de caixa."
            ),
            'valor_total': valor,
        }

    return None


# ---------------------------------------------------------------------------
# RF03.5 — Monitoramento de Campanhas Sanitárias IDARON
# ---------------------------------------------------------------------------

def analisar_campanhas_idaron(total_cabecas_propriedade: int = 0) -> list[AlertaDict]:
    """
    RF03.5 — Verifica campanhas de vacinação ativas com prazo iminente.

    Gera alertas conforme especificação v3.0:
      🔴 ALTA  — prazo_final <= 7 dias sem cobertura completa do rebanho
      🟡 MÉDIA — prazo_final entre 8 e 30 dias sem cobertura completa

    Args:
        total_cabecas_propriedade: total de cabeças na propriedade (para calcular cobertura %).

    Returns:
        Lista de AlertaDict.
    """
    hoje = date.today()
    alertas: list[AlertaDict] = []

    campanhas_ativas = CampanhaVacina.objects.filter(ativa=True, prazo_final__gte=hoje)

    for campanha in campanhas_ativas:
        dias_para_prazo = campanha.dias_para_prazo
        total_doses = campanha.total_doses_aplicadas
        meta = float(campanha.meta_cobertura_percentual)

        # Cobertura em % do rebanho
        cobertura_percentual = 0.0
        if total_cabecas_propriedade > 0:
            cobertura_percentual = (total_doses / total_cabecas_propriedade) * 100

        cobertura_completa = cobertura_percentual >= meta
        sufixo_cobertura = (
            f"{cobertura_percentual:.1f}% de cobertura "
            f"({total_doses} doses aplicadas de {total_cabecas_propriedade} cabeças)"
            if total_cabecas_propriedade > 0
            else f"{total_doses} dose(s) aplicada(s) — total do rebanho não informado"
        )

        if cobertura_completa:
            continue  # Campanha com cobertura atingida — sem alerta

        if dias_para_prazo <= 7:
            alertas.append({
                'tipo': 'CAMPANHA_IDARON_URGENTE',
                'tipo_display': 'Campanha IDARON — Prazo Crítico',
                'prioridade': 'ALTA',
                'produto_id': campanha.vacina_produto.id if campanha.vacina_produto else None,
                'produto_nome': campanha.vacina_produto.nome if campanha.vacina_produto else campanha.nome,
                'unidade': 'dose',
                'saldo': (
                    campanha.vacina_produto.saldo_atual if campanha.vacina_produto else None
                ),
                'estoque_minimo': None,
                'campanha_id': campanha.id,
                'campanha_nome': campanha.nome,
                'dias_para_prazo': dias_para_prazo,
                'justificativa': (
                    f"🔴 URGENTE — Campanha IDARON '{campanha.nome}': prazo em "
                    f"{dias_para_prazo} dia(s) ({campanha.prazo_final.strftime('%d/%m/%Y')}). "
                    f"Cobertura atual: {sufixo_cobertura}. "
                    f"A não vacinação pode resultar em sanções da Defesa Sanitária de Rondônia."
                ),
                'valor_total': None,
            })
        elif dias_para_prazo <= 30:
            alertas.append({
                'tipo': 'CAMPANHA_IDARON_ATENCAO',
                'tipo_display': 'Campanha IDARON — Atenção',
                'prioridade': 'MEDIA',
                'produto_id': campanha.vacina_produto.id if campanha.vacina_produto else None,
                'produto_nome': campanha.vacina_produto.nome if campanha.vacina_produto else campanha.nome,
                'unidade': 'dose',
                'saldo': (
                    campanha.vacina_produto.saldo_atual if campanha.vacina_produto else None
                ),
                'estoque_minimo': None,
                'campanha_id': campanha.id,
                'campanha_nome': campanha.nome,
                'dias_para_prazo': dias_para_prazo,
                'justificativa': (
                    f"🟡 Campanha IDARON '{campanha.nome}': prazo em "
                    f"{dias_para_prazo} dia(s) ({campanha.prazo_final.strftime('%d/%m/%Y')}). "
                    f"Cobertura atual: {sufixo_cobertura}. "
                    f"Agende a vacinação para evitar descumprimento do calendário sanitário."
                ),
                'valor_total': None,
            })

    return alertas


# ---------------------------------------------------------------------------
# RF03.3 — Análise de Suplementação por Lote de Animais
# ---------------------------------------------------------------------------

def analisar_suplementacao_lotes(modo_seca: bool = False) -> list[AlertaDict]:
    """
    RF03.3 — Analisa o consumo de suplementos vinculados aos lotes de animais.

    Usa a fórmula §6.2 (Consumo Diário Global) e §6.3 (Autonomia — floor).
    Classifica a situação de cada lote:
      🔴 ALTA  — < 7 dias de cobertura estimada
      🟡 MÉDIA — 7 a 15 dias de cobertura
      🟢 BAIXA — > 15 dias (situação operacional regular)

    Args:
        modo_seca: True = simulação de início da época de seca (fator 2×).
    """
    alertas: list[AlertaDict] = []
    fator_seca = Decimal('2.0') if modo_seca else Decimal('1.0')

    lotes = LoteAnimais.objects.filter(ativo=True)
    for lote in lotes:
        if not lote.insumo_suplementar:
            continue

        insumo = lote.insumo_suplementar
        duracao_dias = lote.duracao_estimada_insumo(fator_seca=fator_seca)

        # Sem estimativa possível (insumo sem saldo ou consumo zero)
        if duracao_dias is None:
            continue

        consumo_g_cab = int(lote.consumo_diario_cabeca * 1000 * fator_seca)
        sufixo_seca = ' [Simulação de Seca: consumo dobrado]' if modo_seca else ''

        if duracao_dias <= 7:
            alertas.append({
                'tipo': 'SUPLEMENTACAO_CRITICA',
                'tipo_display': f'Suplementação Crítica (< 7 dias)',
                'prioridade': 'ALTA',
                'produto_id': insumo.id,
                'produto_nome': insumo.nome,
                'unidade': insumo.unidade,
                'saldo': insumo.saldo_atual,
                'estoque_minimo': insumo.estoque_minimo,
                'duracao_estimada': f'{duracao_dias} dia(s)',
                'lote_animal_id': lote.id,
                'lote_animal_nome': lote.nome,
                'justificativa': (
                    f"🔴 Suplementação crítica: Estoque de {insumo.nome} dura apenas "
                    f"{duracao_dias} dia(s) para o {lote.nome} "
                    f"({lote.quantidade_cabecas} cab. × {consumo_g_cab} g/cab./dia){sufixo_seca}. "
                    f"Providencie reposição imediata para evitar queda de ECC e perdas zootécnicas."
                ),
                'valor_total': insumo.valor_total_estoque,
            })
        elif duracao_dias <= 15:
            alertas.append({
                'tipo': 'SUPLEMENTACAO_ATENCAO',
                'tipo_display': 'Atenção para Reposição de Suplemento',
                'prioridade': 'MEDIA',
                'produto_id': insumo.id,
                'produto_nome': insumo.nome,
                'unidade': insumo.unidade,
                'saldo': insumo.saldo_atual,
                'estoque_minimo': insumo.estoque_minimo,
                'duracao_estimada': f'{duracao_dias} dia(s)',
                'lote_animal_id': lote.id,
                'lote_animal_nome': lote.nome,
                'justificativa': (
                    f"🟡 Atenção de suplementação: Estoque de {insumo.nome} atende "
                    f"{duracao_dias} dia(s) para o {lote.nome} "
                    f"({lote.quantidade_cabecas} cab. × {consumo_g_cab} g/cab./dia). "
                    f"Avalie reposição em breve para manter o manejo nutricional em dia."
                ),
                'valor_total': insumo.valor_total_estoque,
            })
        else:
            alertas.append({
                'tipo': 'SUPLEMENTACAO_NORMAL',
                'tipo_display': 'Suplementação em Dia',
                'prioridade': 'BAIXA',
                'produto_id': insumo.id,
                'produto_nome': insumo.nome,
                'unidade': insumo.unidade,
                'saldo': insumo.saldo_atual,
                'estoque_minimo': insumo.estoque_minimo,
                'duracao_estimada': f'{duracao_dias} dia(s)',
                'lote_animal_id': lote.id,
                'lote_animal_nome': lote.nome,
                'justificativa': (
                    f"🟢 Suplementação em dia: Estoque de {insumo.nome} com cobertura de "
                    f"{duracao_dias} dia(s) para o {lote.nome} "
                    f"({lote.quantidade_cabecas} cab. × {consumo_g_cab} g/cab./dia). "
                    f"Manejo nutricional operacional."
                ),
                'valor_total': insumo.valor_total_estoque,
            })

    # Alerta sazonal global quando simulação de seca está ativa
    if modo_seca:
        alertas.append({
            'tipo': 'TRANSICAO_SECA',
            'tipo_display': 'Alerta Sazonal — Transição para Época de Seca',
            'prioridade': 'MEDIA',
            'produto_id': None,
            'produto_nome': 'Manejo Nutricional — Época de Seca',
            'unidade': '-',
            'saldo': None,
            'estoque_minimo': None,
            'duracao_estimada': 'Estiagem simulada',
            'justificativa': (
                "🟡 Simulação de início da seca ativada: pastagens sob estresse hídrico com "
                "redução drástica de proteína bruta e digestibilidade. "
                "O consumo de suplemento mineral e proteico foi calculado com fator 2× "
                "para refletir a maior demanda nutricional do rebanho durante a estiagem. "
                "Reforce a suplementação proteico-energética para manter o ECC e "
                "o ganho de peso dos animais."
            ),
            'valor_total': None,
        })

    return alertas


# ---------------------------------------------------------------------------
# RF03.6 — Acompanhamento Temporal (Série para Chart.js)
# ---------------------------------------------------------------------------

def acompanhamento_temporal(produto: Produto) -> dict[str, Any]:
    """
    RF03.6 — Agrupa saídas mensais de um produto para alimentar gráfico Chart.js.

    Returns:
        dict com labels (list[str]), valores (list[float]) e dados_tabela (list[dict]).
    """
    saidas = produto.movimentacoes.filter(tipo='SAIDA').order_by('data_movimentacao')
    meses_nomes = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    agrupado: dict[tuple[int, int], dict] = {}

    for s in saidas:
        chave = (s.data_movimentacao.year, s.data_movimentacao.month)
        if chave not in agrupado:
            rotulo = f"{meses_nomes[chave[1]]}/{str(chave[0])[2:]}"
            agrupado[chave] = {'rotulo': rotulo, 'total': Decimal('0.00'), 'count': 0}
        agrupado[chave]['total'] += s.quantidade
        agrupado[chave]['count'] += 1

    labels, valores, dados_tabela = [], [], []
    for chave in sorted(agrupado.keys()):
        item = agrupado[chave]
        labels.append(item['rotulo'])
        valores.append(float(item['total']))
        media_saida = item['total'] / item['count'] if item['count'] > 0 else Decimal('0')
        dados_tabela.append({
            'rotulo': item['rotulo'],
            'total_saidas': item['total'],
            'num_movimentacoes': item['count'],
            'media_por_saida': media_saida,
        })

    return {'labels': labels, 'valores': valores, 'dados_tabela': dados_tabela}


# ---------------------------------------------------------------------------
# RF02.1 / RF02.2 / RF02.3 — Consolidação e Priorização do Dashboard
# ---------------------------------------------------------------------------

def gerar_alertas_priorizados(
    modo_seca: bool = False,
    total_cabecas_propriedade: int = 0,
) -> list[AlertaDict]:
    """
    RF02.1 / RF02.2 / RF02.3 — Consolida e prioriza todos os alertas do
    sistema em estilo To-Do List semafórico.

    Ordena: 🔴 ALTA → 🟡 MÉDIA → 🟢 BAIXA.
    Dentro do mesmo nível de prioridade, mantém a ordem de inserção.

    Args:
        modo_seca: True ativa simulação sazonal de seca.
        total_cabecas_propriedade: total de cabeças para calcular cobertura de campanhas.

    Returns:
        Lista ordenada de AlertaDict prontos para renderização no template.
    """
    alertas: list[AlertaDict] = []
    produtos = Produto.objects.filter(ativo=True)

    for p in produtos:
        if p.categoria in ('MAQUINAS', 'VEICULOS'):
            continue

        # 1. Estoque Crítico e Falta (RF03.1)
        alerta_critico = calcular_estoque_critico(p)
        if alerta_critico:
            alertas.append(alerta_critico)

        # 2. Validades e Risco de Perdas (RF03.2 / §6.4)
        alertas.extend(analisar_validade(p))

        # 3. Anomalias de Saída (RF03.4 / §6.5)
        alerta_anomalia = detectar_anomalias(p)
        if alerta_anomalia:
            alertas.append(alerta_anomalia)

        # 4. Excesso / Capital Parado (RF03.7)
        alerta_financeiro = analisar_financeiro(p)
        if alerta_financeiro:
            alertas.append(alerta_financeiro)

    # 5. Suplementação e Manejo por Lotes de Gado (RF03.3)
    alertas.extend(analisar_suplementacao_lotes(modo_seca=modo_seca))

    # 6. Campanhas Sanitárias IDARON (RF03.5)
    alertas.extend(analisar_campanhas_idaron(total_cabecas_propriedade=total_cabecas_propriedade))

    # Ordenação por prioridade (🔴 1 → 🟡 2 → 🟢 3)
    _peso = {'ALTA': 1, 'MEDIA': 2, 'BAIXA': 3}
    alertas.sort(key=lambda a: _peso.get(a.get('prioridade', 'BAIXA'), 99))

    return alertas
