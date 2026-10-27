from django.contrib import admin
from .models import AtivoRural, Lote, ManutencaoAtivo, Movimentacao, Produto, TransferenciaRecurso


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'unidade', 'saldo_atual_display', 'estoque_minimo', 'preco_referencia', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome', 'tipo_item')

    def saldo_atual_display(self, obj):
        return f"{obj.saldo_atual} {obj.unidade}"
    saldo_atual_display.short_description = "Saldo Atual"


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('numero_lote', 'produto', 'data_validade', 'saldo_lote_display')
    list_filter = ('produto__categoria', 'data_validade')
    search_fields = ('numero_lote', 'produto__nome')

    def saldo_lote_display(self, obj):
        return f"{obj.saldo_lote} {obj.produto.unidade}"
    saldo_lote_display.short_description = "Saldo do Lote"


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('data_movimentacao', 'produto', 'tipo', 'quantidade_display', 'ativo', 'origem_recurso', 'lote', 'destino', 'responsavel')
    list_filter = ('tipo', 'produto__categoria', 'data_movimentacao')
    search_fields = ('produto__nome', 'destino', 'responsavel')

    def quantidade_display(self, obj):
        return f"{obj.quantidade} {obj.produto.unidade}"
    quantidade_display.short_description = "Quantidade"


@admin.register(AtivoRural)
class AtivoRuralAdmin(admin.ModelAdmin):
    list_display = ('produto', 'status_manutencao', 'consumo_medio', 'unidade_consumo')
    list_filter = ('status_manutencao',)
    search_fields = ('produto__nome', 'produto__tipo_item', 'produto__placa')


@admin.register(ManutencaoAtivo)
class ManutencaoAtivoAdmin(admin.ModelAdmin):
    list_display = ('data', 'ativo', 'tipo', 'descricao', 'custo', 'fornecedor')
    list_filter = ('tipo', 'data')
    search_fields = ('ativo__produto__nome', 'descricao', 'fornecedor')


@admin.register(TransferenciaRecurso)
class TransferenciaRecursoAdmin(admin.ModelAdmin):
    list_display = ('data', 'produto_origem', 'quantidade_origem', 'produto_destino', 'quantidade_destino', 'origem_recurso', 'destino_tipo')
    list_filter = ('origem_recurso', 'destino_tipo', 'data')
    search_fields = ('produto_origem__nome', 'produto_destino__nome', 'local_destino')
