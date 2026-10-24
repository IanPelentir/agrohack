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

    def clean(self):
        super().clean()
        if self.tipo == 'SAIDA' and self.quantidade is not None and getattr(self, 'produto_id', None):
            saldo = self.produto.saldo_atual
            if self.pk:
                antiga = Movimentacao.objects.filter(pk=self.pk).first()
                if antiga and antiga.tipo == 'SAIDA':
                    saldo += antiga.quantidade
            if self.quantidade > saldo:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Operação não permitida (RN01.1): Saída de {self.quantidade} {self.produto.unidade} "
                    f"excede o saldo disponível ({saldo} {self.produto.unidade})."
                )

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.quantidade} {self.produto.unidade} em {self.data_movimentacao}"


class LoteAnimais(models.Model):
    CATEGORIAS = [
        ('CORTE', 'Gado de Corte'),
        ('LEITE', 'Gado de Leite'),
        ('CRIA', 'Cria / Bezerros'),
        ('RECRIA', 'Recria / Garrotes'),
        ('ENGORDA', 'Terminação / Engorda'),
    ]

    nome = models.CharField(max_length=120, unique=True, verbose_name="Identificação do Lote")
    categoria = models.CharField(max_length=40, choices=CATEGORIAS, default='CORTE', verbose_name="Categoria")
    quantidade_cabecas = models.PositiveIntegerField(verbose_name="Quantidade de Cabeças")
    pasto_localizacao = models.CharField(max_length=120, verbose_name="Pasto / Localização")
    escore_corporal = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('3.0'), verbose_name="Escore Corporal (ECC 1-5)")
    peso_medio_estimado = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Peso Médio Estimado (kg)")
    consumo_diario_cabeca = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal('0.120'), verbose_name="Consumo Diário por Cabeça (kg/dia)")
    insumo_suplementar = models.ForeignKey(Produto, on_delete=models.SET_NULL, null=True, blank=True, related_name='lotes_consumidores', verbose_name="Insumo Suplementar Vinculado")
    observacoes = models.TextField(blank=True, verbose_name="Observações do Manejo")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lote de Animais"
        verbose_name_plural = "Lotes de Animais"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.quantidade_cabecas} cab) - {self.pasto_localizacao}"

    @property
    def consumo_diario_total_kg(self):
        """Consumo diário total do lote em kg."""
        return Decimal(str(self.quantidade_cabecas)) * self.consumo_diario_cabeca

    def duracao_estimada_insumo(self, fator_seca=Decimal('1.0')):
        """Calcula dias restantes de insumo suplementar para este lote."""
        if not self.insumo_suplementar:
            return None
        saldo = self.insumo_suplementar.saldo_atual
        if saldo <= 0:
            return 0
        unidade = self.insumo_suplementar.unidade.lower()
        saldo_kg = saldo
        if 'sc' in unidade or 'saco' in unidade:
            saldo_kg = saldo * Decimal('30.0')
        consumo_dia = self.consumo_diario_total_kg * fator_seca
        if consumo_dia <= 0:
            return None
        import math
        return math.ceil(float(saldo_kg / consumo_dia))


