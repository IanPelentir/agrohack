"""
Módulo de análises inteligentes do estoque rural — AgroHack 2026/2.
Implementação estrita e determinística conforme RF03.1 a RF03.6 e RF02.1 a RF02.3.
"""

from datetime import date, timedelta
from decimal import Decimal
import math
from django.db.models import Sum, Avg
from .models import Produto, Lote, Movimentacao, LoteAnimais


def estimar_duracao(produto, janela_dias=30):
    """
    RF03.3: Estima a duração restante do estoque (dias) com base no consumo médio diário.
    Regra segura: apenas calcula se houver saldo positivo e pelo menos 2 saídas na janela.
    Sem histórico suficiente, retorna None e motivo explicativo (RN03).
    """
    saldo = produto.saldo_atual
    if saldo <= 0:
        return {
            'dias': 0,
            'consumo_diario': Decimal('0.00'),
            'justificativa': 'Saldo zerado ou negativo',
            'estimado': True
        }

    hoje = date.today()
    data_limite = hoje - timedelta(days=janela_dias)

    saidas = produto.movimentacoes.filter(
        tipo='SAIDA',
        data_movimentacao__gte=data_limite
    )

    qtd_saidas = saidas.count()
    if qtd_saidas < 2:
        return {
            'dias': None,
            'consumo_diario': None,
            'justificativa': 'Não estimado: histórico insuficiente de saídas recentes (mínimo 2 registros)',
            'estimado': False
        }

    total_saidas = saidas.aggregate(total=Sum('quantidade'))['total'] or Decimal('0.00')
    if total_saidas <= 0:
        return {
            'dias': None,
            'consumo_diario': Decimal('0.00'),
            'justificativa': 'Não estimado: sem consumo registrado no período',
            'estimado': False
        }

    consumo_diario = total_saidas / Decimal(str(janela_dias))
    dias_estimados = math.ceil(float(saldo / consumo_diario))

    return {
        'dias': dias_estimados,
        'consumo_diario': consumo_diario,
        'justificativa': f'Consumo médio de {consumo_diario:.2f} {produto.unidade}/dia nos últimos {janela_dias} dias',
        'estimado': True
    }


def calcular_estoque_critico(produto):
    """
    RF03.1: Identifica produtos com risco de falta / estoque crítico.
    Regra da equipe (D3):
      - Saldo <= 0: ALTA (Vermelho) - Ruptura imediata
      - Saldo <= estoque_minimo: ALTA (Vermelho) - Estoque Crítico
      - Saldo <= 1.5 * estoque_minimo: MEDIA (Amarelo) - Atenção
      - Saldo > 1.5 * estoque_minimo: BAIXA / NORMAL (Verde)
    """
    saldo = produto.saldo_atual
    minimo = produto.estoque_minimo

    # Ruptura emergencial (saldo zerado ou negativo)
    if saldo <= 0:
        return {
            'tipo': 'ESTOQUE_CRITICO',
            'tipo_display': 'Estoque Crítico (Esgotado)',
            'prioridade': 'ALTA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'justificativa': f"Estoque crítico / Esgotado: Saldo atual ({saldo} {produto.unidade}) está zerado ou negativo. Reposição imediata recomendada.",
            'valor_total': Decimal('0.00'),
        }

    if minimo is None:
        return None

    if saldo <= minimo:
        estimativa = estimar_duracao(produto)
        dias_texto = f" — estimado para ~{estimativa['dias']} dia(s)" if estimativa['dias'] else ""
        return {
            'tipo': 'ESTOQUE_CRITICO',
            'tipo_display': 'Estoque Crítico',
            'prioridade': 'ALTA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'justificativa': f"Estoque crítico: Saldo atual ({saldo} {produto.unidade}) atingiu o limite mínimo ({minimo} {produto.unidade}){dias_texto}.",
            'valor_total': produto.valor_total_estoque,
        }
    elif saldo <= (minimo * Decimal('1.5')):
        return {
            'tipo': 'ESTOQUE_ATENCAO',
            'tipo_display': 'Atenção para Reposição',
            'prioridade': 'MEDIA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': saldo,
            'estoque_minimo': minimo,
            'justificativa': f"Estoque em atenção: Saldo atual ({saldo} {produto.unidade}) está próximo ao mínimo ({minimo} {produto.unidade}).",
            'valor_total': produto.valor_total_estoque,
        }

    return None



def analisar_validade(produto, dias_alerta=30):
    """
    RF03.2: Análise de Validade e Risco de Perdas.
    Cruza a data de validade dos lotes com o estoque restante e ritmo de consumo.
    """
    hoje = date.today()
    lotes = produto.lotes.filter(data_validade__isnull=False)
    alertas = []

    for lote in lotes:
        saldo_lote = lote.saldo_lote
        if saldo_lote <= 0:
            continue

        dias_restantes = (lote.data_validade - hoje).days

        if dias_restantes < 0:
            alertas.append({
                'tipo': 'LOTE_VENCIDO',
                'tipo_display': 'Lote Vencido',
                'prioridade': 'ALTA',
                'produto_id': produto.id,
                'produto_nome': produto.nome,
                'lote': lote.numero_lote,
                'validade': lote.data_validade,
                'unidade': produto.unidade,
                'saldo': saldo_lote,
                'estoque_minimo': produto.estoque_minimo,
                'justificativa': f"Lote {lote.numero_lote} vencido há {abs(dias_restantes)} dia(s) com {saldo_lote} {produto.unidade} ainda em estoque. Descarte ou destinação imediata recomendada.",
                'valor_total': (saldo_lote * produto.preco_referencia) if produto.preco_referencia else None,
            })
        elif dias_restantes <= dias_alerta:
            estimativa = estimar_duracao(produto)
            consumo_diario = estimativa.get('consumo_diario')

            if consumo_diario and consumo_diario > 0:
                consumo_projetado = consumo_diario * Decimal(str(dias_restantes))
                if saldo_lote > consumo_projetado:
                    sobra = saldo_lote - consumo_projetado
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
                        'estoque_minimo': produto.estoque_minimo,
                        'justificativa': f"Risco de perda: Lote {lote.numero_lote} vence em {dias_restantes} dias. No ritmo atual de consumo, cerca de {sobra:.1f} {produto.unidade} não serão consumidos a tempo.",
                        'valor_total': (saldo_lote * produto.preco_referencia) if produto.preco_referencia else None,
                    })
                    continue

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
                'justificativa': f"Lote {lote.numero_lote} próximo do vencimento (restam {dias_restantes} dias). Recomenda-se priorizar o uso deste lote.",
                'valor_total': (saldo_lote * produto.preco_referencia) if produto.preco_referencia else None,
            })

    return alertas


def detectar_anomalias(produto):
    """
    RF03.4: Detecção de Anomalias de Saída.
    Decisão da equipe (D4): desvio padrão (> 2 sigma) com mínimo de 5 registros de saída.
    """
    saidas = produto.movimentacoes.filter(tipo='SAIDA')
    if saidas.count() < 5:
        return None

    quantidades = [float(m.quantidade) for m in saidas]
    media = sum(quantidades) / len(quantidades)
    variancia = sum((x - media) ** 2 for x in quantidades) / len(quantidades)
    desvio_padrao = math.sqrt(variancia)

    if desvio_padrao == 0:
        return None

    limite_superior = media + (2 * desvio_padrao)

    # Verifica saídas recentes (últimas 3)
    saidas_recentes = list(saidas[:3])
    for s in saidas_recentes:
        if float(s.quantidade) > limite_superior:
            return {
                'tipo': 'ANOMALIA_SAIDA',
                'tipo_display': 'Saída Atípica',
                'prioridade': 'MEDIA',
                'produto_id': produto.id,
                'produto_nome': produto.nome,
                'unidade': produto.unidade,
                'saldo': produto.saldo_atual,
                'estoque_minimo': produto.estoque_minimo,
                'justificativa': f"Saída atípica de {s.quantidade} {produto.unidade} em {s.data_movimentacao.strftime('%d/%m/%Y')} foi superior ao padrão histórico (média de {media:.1f} e desvio de {desvio_padrao:.1f}). Destino: {s.destino or 'Não informado'}.",
                'valor_total': produto.valor_total_estoque,
            }

    return None


def analisar_financeiro(produto):
    """
    RF03.5: Análise Financeira e Excesso de Estoque.
    Identifica alto capital parado com baixa rotação (>90 dias de cobertura ou saldo > 3x o mínimo).
    """
    valor = produto.valor_total_estoque
    if valor is None or valor < Decimal('5000.00'):
        return None

    if produto.estoque_minimo and produto.saldo_atual >= (produto.estoque_minimo * Decimal('3.0')):
        return {
            'tipo': 'EXCESSO_ESTOQUE',
            'tipo_display': 'Capital Parado / Excesso',
            'prioridade': 'BAIXA',
            'produto_id': produto.id,
            'produto_nome': produto.nome,
            'unidade': produto.unidade,
            'saldo': produto.saldo_atual,
            'estoque_minimo': produto.estoque_minimo,
            'justificativa': f"Capital imobilizado expressivo (R$ {valor:,.2f}) com saldo atual ({produto.saldo_atual} {produto.unidade}) 3 vezes acima do estoque mínimo. Evitar novas compras no curto prazo.",
            'valor_total': valor,
        }

    return None


def acompanhamento_temporal(produto):
    """
    RF03.6: Agrupa saídas por mês para alimentar o gráfico interativo Chart.js.
    """
    saidas = produto.movimentacoes.filter(tipo='SAIDA').order_by('data_movimentacao')
    
    agrupado = {}
    meses_nomes = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    for s in saidas:
        chave = (s.data_movimentacao.year, s.data_movimentacao.month)
        if chave not in agrupado:
            rotulo = f"{meses_nomes[chave[1]]}/{str(chave[0])[2:]}"
            agrupado[chave] = {
                'rotulo': rotulo,
                'total': Decimal('0.00'),
                'count': 0
            }
        agrupado[chave]['total'] += s.quantidade
        agrupado[chave]['count'] += 1

    labels = []
    valores = []
    dados_tabela = []

    for chave in sorted(agrupado.keys()):
        item = agrupado[chave]
        labels.append(item['rotulo'])
        valores.append(float(item['total']))
        media_saida = item['total'] / item['count'] if item['count'] > 0 else 0
        dados_tabela.append({
            'rotulo': item['rotulo'],
            'total_saidas': item['total'],
            'num_movimentacoes': item['count'],
            'media_por_saida': media_saida,
            'is_anomalia': False
        })

    return {
        'labels': labels,
        'valores': valores,
        'dados_tabela': dados_tabela
    }


def analisar_suplementacao_lotes(modo_seca=False):
    """
    Analisa o consumo de suplementos e insumos vinculados aos lotes de animais (LoteAnimais).
    - 🔴 Crítico (< 7 dias de consumo estimado pelo lote ou falta de insumo)
    - 🟡 Atenção (7 a 15 dias de consumo ou alerta sazonal de transição)
    - 🟢 Normal (> 15 dias de consumo em dia)
    """
    alertas = []
    fator_seca = Decimal('2.0') if modo_seca else Decimal('1.0')

    lotes = LoteAnimais.objects.filter(ativo=True)
    for lote in lotes:
        if not lote.insumo_suplementar:
            continue

        insumo = lote.insumo_suplementar
        duracao_dias = lote.duracao_estimada_insumo(fator_seca=fator_seca)

        consumo_g = int(lote.consumo_diario_cabeca * 1000 * fator_seca)

        if duracao_dias is None:
            continue

        if duracao_dias <= 7:
            justificativa = (
                f"O {insumo.nome} dura apenas {duracao_dias} dia(s) para o {lote.nome} "
                f"({lote.quantidade_cabecas} cab.) consumindo {consumo_g}g/cabeça/dia"
                f"{' [Simulação de Início da Seca Ativada: consumo acelerado]' if modo_seca else ''}."
            )
            alertas.append({
                'tipo': 'SUPLEMENTACAO_CRITICA',
                'tipo_display': 'Suplementação Crítica (< 7 dias)',
                'prioridade': 'ALTA',
                'produto_id': insumo.id,
                'produto_nome': insumo.nome,
                'unidade': insumo.unidade,
                'saldo': insumo.saldo_atual,
                'estoque_minimo': insumo.estoque_minimo,
                'duracao_estimada': f"{duracao_dias} dia(s)",
                'justificativa': justificativa,
                'valor_total': insumo.valor_total_estoque,
                'lote_animal_id': lote.id,
                'lote_animal_nome': lote.nome,
            })
        elif duracao_dias <= 15:
            justificativa = (
                f"Atenção para reposição: Estoque de {insumo.nome} atende apenas {duracao_dias} dia(s) para o {lote.nome} "
                f"({lote.quantidade_cabecas} cab.) consumindo {consumo_g}g/cabeça/dia."
            )
            alertas.append({
                'tipo': 'SUPLEMENTACAO_ATENCAO',
                'tipo_display': 'Atenção para Reposição de Suplemento',
                'prioridade': 'MEDIA',
                'produto_id': insumo.id,
                'produto_nome': insumo.nome,
                'unidade': insumo.unidade,
                'saldo': insumo.saldo_atual,
                'estoque_minimo': insumo.estoque_minimo,
                'duracao_estimada': f"{duracao_dias} dia(s)",
                'justificativa': justificativa,
                'valor_total': insumo.valor_total_estoque,
                'lote_animal_id': lote.id,
                'lote_animal_nome': lote.nome,
            })
        else:
            justificativa = (
                f"Operação em dia: Suplementação de {insumo.nome} com cobertura de {duracao_dias} dia(s) "
                f"para o {lote.nome} ({lote.quantidade_cabecas} cab.) consumindo {consumo_g}g/cabeça/dia."
            )
            alertas.append({
                'tipo': 'SUPLEMENTACAO_NORMAL',
                'tipo_display': 'Suplementação em Dia',
                'prioridade': 'BAIXA',
                'produto_id': insumo.id,
                'produto_nome': insumo.nome,
                'unidade': insumo.unidade,
                'saldo': insumo.saldo_atual,
                'estoque_minimo': insumo.estoque_minimo,
                'duracao_estimada': f"{duracao_dias} dia(s)",
                'justificativa': justificativa,
                'valor_total': insumo.valor_total_estoque,
                'lote_animal_id': lote.id,
                'lote_animal_nome': lote.nome,
            })

    if modo_seca:
        alertas.append({
            'tipo': 'TRANSICAO_SECA',
            'tipo_display': 'Alerta Sazonal: Transição para Época de Seca',
            'prioridade': 'MEDIA',
            'produto_id': None,
            'produto_nome': 'Manejo Nutricional na Seca',
            'unidade': '-',
            'saldo': None,
            'estoque_minimo': None,
            'duracao_estimada': 'Estiagem Ativa',
            'justificativa': 'Início da seca simulado: Pastagens sob estresse hídrico com queda drástica de proteína bruta. Suplementação proteico-energética deve ser reforçada para sustentar o ganho de peso e o ECC do rebanho.',
            'valor_total': None,
        })

    return alertas


def gerar_alertas_priorizados(modo_seca=False):
    """
    RF02.1 / RF02.2 / RF02.3: Consolida e prioriza todos os alertas do estoque e dos lotes de gado em estilo To-Do List.
    Ordena: ALTA (Vermelho) -> MEDIA (Amarelo) -> BAIXA (Verde).
    """
    alertas = []
    produtos = Produto.objects.filter(ativo=True)

    for p in produtos:
        # 1. Estoque Crítico
        alerta_critico = calcular_estoque_critico(p)
        if alerta_critico:
            alertas.append(alerta_critico)

        # 2. Validades e Perdas
        alertas_validade = analisar_validade(p)
        alertas.extend(alertas_validade)

        # 3. Anomalias
        alerta_anomalia = detectar_anomalias(p)
        if alerta_anomalia:
            alertas.append(alerta_anomalia)

        # 4. Financeiro / Excesso
        alerta_financeiro = analisar_financeiro(p)
        if alerta_financeiro:
            alertas.append(alerta_financeiro)

    # 5. Suplementação e Manejo por Lotes de Gado (LoteAnimais)
    alertas_lotes = analisar_suplementacao_lotes(modo_seca=modo_seca)
    alertas.extend(alertas_lotes)

    # Ordenar por prioridade
    peso_prioridade = {'ALTA': 1, 'MEDIA': 2, 'BAIXA': 3}
    alertas.sort(key=lambda a: peso_prioridade.get(a.get('prioridade', 'BAIXA'), 99))

    return alertas
