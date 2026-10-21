from django.db import models
from django.utils import timezone
from decimal import Decimal


class Produto(models.Model):
    CATEGORIAS = [
        ('DEFENSIVOS', 'Defensivos Agrícolas'),
        ('FERTILIZANTES', 'Fertilizantes e Corretivos'),
        ('SEMENTES', 'Sementes e Mudas'),
        ('MEDICAMENTOS', 'Medicamentos Veterinários'),
        ('COMBUSTIVEIS', 'Combustíveis e Lubrificantes'),
        ('SUPLEMENTOS', 'Suplementos Minerais e Rações'),
        ('MANUTENCAO', 'Peças e Manutenção'),
        ('EPI', 'Equipamentos e EPIs'),
    ]

    nome = models.CharField(max_length=150, unique=True, verbose_name="Nome do Insumo")
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default='DEFENSIVOS', verbose_name="Categoria")
    unidade = models.CharField(max_length=20, verbose_name="Unidade de Medida")  # kg, L, sc, frasco, un, dose
    estoque_minimo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Estoque Mínimo")
    preco_referencia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Preço de Referência (R$)")
    descricao = models.TextField(blank=True, verbose_name="Observações / Descrição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.unidade})"

    @property
    def saldo_atual(self):
        entradas = self.movimentacoes.filter(tipo='ENTRADA').aggregate(total=models.Sum('quantidade'))['total'] or Decimal('0.00')
        saidas = self.movimentacoes.filter(tipo='SAIDA').aggregate(total=models.Sum('quantidade'))['total'] or Decimal('0.00')
        return entradas - saidas

    @property
    def valor_total_estoque(self):
        if self.preco_referencia is not None:
            saldo = self.saldo_atual
            if saldo > 0:
                return saldo * self.preco_referencia
        return None


class Lote(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='lotes', verbose_name="Produto")
    numero_lote = models.CharField(max_length=60, verbose_name="Número do Lote")
    data_validade = models.DateField(null=True, blank=True, verbose_name="Data de Validade")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        unique_together = ('produto', 'numero_lote')
        ordering = ['data_validade', 'numero_lote']

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.produto.nome}"

    @property
    def saldo_lote(self):
        entradas = self.movimentacoes.filter(tipo='ENTRADA').aggregate(total=models.Sum('quantidade'))['total'] or Decimal('0.00')
        saidas = self.movimentacoes.filter(tipo='SAIDA').aggregate(total=models.Sum('quantidade'))['total'] or Decimal('0.00')
        return entradas - saidas


class Movimentacao(models.Model):
    TIPOS = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes', verbose_name="Produto")
    lote = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentacoes', verbose_name="Lote")
    tipo = models.CharField(max_length=10, choices=TIPOS, verbose_name="Tipo de Movimentação")
    quantidade = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Quantidade")
    data_movimentacao = models.DateField(default=timezone.now, verbose_name="Data da Movimentação")
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Preço Unitário (R$)")
    fornecedor = models.CharField(max_length=150, blank=True, verbose_name="Fornecedor")
    destino = models.CharField(max_length=150, blank=True, verbose_name="Destino da Retirada")
    responsavel = models.CharField(max_length=100, blank=True, verbose_name="Responsável")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_movimentacao', '-id']

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.quantidade} {self.produto.unidade} em {self.data_movimentacao}"

