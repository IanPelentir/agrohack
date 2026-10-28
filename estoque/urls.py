from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # RF02: Painel Principal "To-Do List"
    path('', views.painel, name='painel'),
    path('pendencias/nova/', views.pendencia_nova, name='pendencia_nova'),
    path('pendencias/<int:pk>/status/', views.pendencia_status, name='pendencia_status'),
    path('pendencias/nova/', views.pendencia_nova, name='pendencia_nova'),
    path('pendencias/<int:pk>/status/', views.pendencia_status, name='pendencia_status'),

    # Consulta organizada de produtos
    path('produtos/', views.produto_lista, name='produto_lista'),
    path('produtos/novo/', views.produto_novo, name='produto_novo'),
    path('produtos/<int:pk>/editar/', views.produto_editar, name='produto_editar'),
    path('produtos/<int:pk>/excluir/', views.produto_excluir, name='produto_excluir'),
    path('produtos/<int:pk>/', views.produto_detalhe, name='produto_detalhe'),

    # RF03.6: Acompanhamento Temporal
    path('consumo/', views.consumo, name='consumo'),
    path('consumo/<int:pk>/', views.consumo_produto, name='consumo_produto'),

    # RF01: Importação de dados
    path('importar/', views.importar, name='importar'),
    path('importar/confirmar/', views.confirmar_importacao, name='confirmar_importacao'),
    path('importar/demonstracao/', views.carregar_demonstracao, name='carregar_demonstracao'),

    # RF01.3: Registro de movimentação para reanálise
    path('movimentacoes/nova/', views.movimentacao_nova, name='movimentacao_nova'),
    path('recursos/', views.recursos, name='recursos'),
    path('recursos/ativos/<int:pk>/atualizar/', views.ativo_atualizar, name='ativo_atualizar'),
    path('recursos/manutencoes/nova/', views.manutencao_nova, name='manutencao_nova'),
    path('recursos/transferencias/nova/', views.transferencia_nova, name='transferencia_nova'),

    # Gestão Amigável de Lotes de Gado (LoteAnimais)
    path('lotes/novo/', views.lote_novo, name='lote_novo'),
    path('lotes/<int:pk>/mortalidade/', views.lote_mortalidade, name='lote_mortalidade'),
    path('lotes/<int:pk>/editar/', views.lote_editar, name='lote_editar'),
    path('lotes/<int:pk>/excluir/', views.lote_excluir, name='lote_excluir'),
]
