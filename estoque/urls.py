from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # RF02: Painel Principal "To-Do List"
    path('', views.painel, name='painel'),

    # Consulta organizada de produtos
    path('produtos/', views.produto_lista, name='produto_lista'),
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

    # Gestão Amigável de Lotes de Gado (LoteAnimais)
    path('lotes/novo/', views.lote_novo, name='lote_novo'),
    path('lotes/<int:pk>/editar/', views.lote_editar, name='lote_editar'),
    path('lotes/<int:pk>/excluir/', views.lote_excluir, name='lote_excluir'),
]
