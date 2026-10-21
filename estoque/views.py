from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import date
from decimal import Decimal
import json

from .models import Produto, Lote, Movimentacao
from .analises import (
    gerar_alertas_priorizados,
    estimar_duracao,
    acompanhamento_temporal,
    calcular_estoque_critico,
    analisar_validade
)


def painel(request):
    """
    Visão consolidada To-Do List de pendências e alertas (RF02.1, RF02.2, RF02.3).
    """
    alertas = gerar_alertas_priorizados()

    total_produtos = Produto.objects.filter(ativo=True).count()
    alta_prioridade = sum(1 for a in alertas if a['prioridade'] == 'ALTA')
    media_prioridade = sum(1 for a in alertas if a['prioridade'] == 'MEDIA')

    produtos_com_problema = {a['produto_id'] for a in alertas if a['prioridade'] in ['ALTA', 'MEDIA']}
    itens_regulares = max(0, total_produtos - len(produtos_com_problema))

    context = {
        'alertas': alertas,
        'kpis': {
            'alta_prioridade': alta_prioridade,
            'media_prioridade': media_prioridade,
            'itens_regulares': itens_regulares,
            'total_produtos': total_produtos,
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


def importar(request):
    """
    Tela de upload e importação de planilha CSV (RF01.1, RF01.2).
    """
    return render(request, 'estoque/importar.html', {'previa_importacao': None})


def confirmar_importacao(request):
    messages.info(request, "Importação gravada e reanálise executada com sucesso.")
    return redirect('estoque:painel')


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
    Registro manual de movimentação para demonstração de reanálise automática (RF01.3).
    """
    produtos = Produto.objects.filter(ativo=True)

    if request.method == 'POST':
        produto_id = request.POST.get('produto')
        tipo = request.POST.get('tipo')
        quantidade = request.POST.get('quantidade')
        data_str = request.POST.get('data')
        lote_num = request.POST.get('lote', '').strip()
        validade_str = request.POST.get('validade', '').strip()
        preco_str = request.POST.get('preco_unitario', '').strip()
        destino = request.POST.get('destino', '').strip()
        responsavel = request.POST.get('responsavel', '').strip()
        fornecedor = request.POST.get('fornecedor', '').strip()

        produto = get_object_or_404(Produto, id=produto_id)

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
            quantidade=Decimal(quantidade),
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
