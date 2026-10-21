from django.contrib import admin
from .models import Produto, Lote, Movimentacao


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'unidade', 'saldo_atual_display', 'estoque_minimo', 'preco_referencia', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome',)

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
    list_display = ('data_movimentacao', 'produto', 'tipo', 'quantidade_display', 'lote', 'destino', 'responsavel')
    list_filter = ('tipo', 'produto__categoria', 'data_movimentacao')
    search_fields = ('produto__nome', 'destino', 'responsavel')

    def quantidade_display(self, obj):
        return f"{obj.quantidade} {obj.produto.unidade}"
    quantidade_display.short_description = "Quantidade"
