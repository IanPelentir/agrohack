"""
models.py — AGROGADO: Sistema de Gestão Inteligente de Insumos Rurais
AgroHack 2026/2 — IFRO Campus Ariquemes

Entidades implementadas:
  - Produto: insumo rural com os 13 campos oficiais do regulamento
  - Lote: rastreabilidade de lote/validade por produto (RF01.2 campos 9 e 10)
  - Movimentacao: registro de entrada/saída com todos os 13 campos (RF01.2)
  - LoteAnimais: rebanho bovino por lote (corte/leite) com ECC e suplementação (RF03.4)
  - CampanhaVacina: campanhas sanitárias obrigatórias IDARON (RF03.5)
  - RegistroVacinacaoLote: aplicação de vacina por lote com abatimento de estoque (RF03.5)
  - GuiaTransitoAnimal: GTA para rastreamento de entradas/saídas do rebanho (RF03.6)

Regras de negócio garantidas:
  - RN01: Incompatibilidade de unidades (campo `unidade` por produto é canônico)
  - RN01.1: Bloqueio de saldo negativo via clean() na Movimentacao
  - RN02: Campos opcionais preservados como None, nunca convertidos para zero
  - RN04: Arquitetura puramente determinística — sem IA generativa
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Produto (Insumo Rural) — âncora dos 13 campos do regulamento
# ---------------------------------------------------------------------------

class Produto(models.Model):
    """
    Representa um insumo rural com suporte estrito aos 13 campos do regulamento
    oficial do AgroHack 2026/2 (RF01.2).

    Campos dos 13 oficiais armazenados aqui:
      campo 1 — produto (campo `nome`)
      campo 2 — categoria
      campo 3 — unidade
      campo 5 — estoque_minimo

    Os campos 4, 6, 7, 8, 9, 10, 11, 12, 13 são armazenados em
    Movimentacao/Lote para respeitar a estrutura transacional do regulamento.
    """

    CATEGORIAS = [
        ('INSUMOS',       'Insumos Gerais'),
        ('DEFENSIVOS',    'Defensivos Agrícolas'),
        ('FERTILIZANTES', 'Fertilizantes e Corretivos'),
        ('SEMENTES',      'Sementes e Mudas'),
        ('MEDICAMENTOS',  'Medicamentos Veterinários'),
        ('COMBUSTIVEIS',  'Combustíveis, Óleos e Lubrificantes'),
        ('SUPLEMENTOS',   'Suplementos Minerais e Rações'),
        ('PECUARIA',      'Materiais de Pecuária'),
        ('MAQUINAS',      'Máquinas e Implementos Agrícolas'),
        ('VEICULOS',      'Veículos e Automóveis Rurais'),
        ('FERRAMENTAS',   'Ferramentas e Utensílios'),
        ('MANUTENCAO',    'Peças e Manutenção'),
        ('MATERIAIS_CONSTRUCAO', 'Materiais de Construção e Cerca'),
        ('EPI',           'Equipamentos e EPIs'),
        ('OUTROS',        'Outros Itens da Fazenda'),
    ]

    TIPOS_EMBALAGEM = [
        ('UNIDADE', 'Unidade'),
        ('SACO', 'Saco'),
        ('FRASCO', 'Frasco'),
        ('CAIXA', 'Caixa'),
        ('GRANEL', 'Granel'),
        ('TAMBOR', 'Tambor'),
    ]

    # Campo 1 — produto
    nome = models.CharField(
        max_length=150, unique=True, verbose_name="Nome do Item",
        help_text="Nome comercial ou identificação do item da propriedade."
    )
    # Campo 2 — categoria
    categoria = models.CharField(
        max_length=50, choices=CATEGORIAS, default='DEFENSIVOS',
        verbose_name="Categoria",
        help_text="Categoria operacional do insumo (campo 2 do regulamento)."
    )
    tipo_item = models.CharField(
        max_length=100, blank=True, verbose_name="Tipo específico",
        help_text="Descrição livre, como caminhonete, trator, óleo 15W40 ou chave de roda."
    )
    # Campo 3 — unidade (canônica por produto — RN01)
    unidade = models.CharField(
        max_length=20, verbose_name="Unidade de Medida",
        help_text=(
            "Unidade canônica do produto (kg, L, sc, frasco, dose, un). "
            "Não misturar com outras unidades no mesmo produto (RN01)."
        )
    )
    tipo_embalagem = models.CharField(
        max_length=20, choices=TIPOS_EMBALAGEM, default='UNIDADE',
        verbose_name="Tipo de Embalagem"
    )
    embalagem_em_caixa = models.BooleanField(
        default=False, verbose_name="Armazenado em caixa"
    )
    peso_embalagem_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        verbose_name="Peso por embalagem (kg)"
    )
    volume_embalagem_ml = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Volume por embalagem (ml)"
    )
    fabricante = models.CharField(max_length=120, blank=True, verbose_name="Fabricante")
    modelo = models.CharField(max_length=120, blank=True, verbose_name="Modelo")
    numero_serie = models.CharField(max_length=100, blank=True, verbose_name="Número de série / patrimônio")
    placa = models.CharField(max_length=10, blank=True, verbose_name="Placa")
    chassi = models.CharField(max_length=30, blank=True, verbose_name="Chassi")
    ano_fabricacao = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Ano de fabricação"
    )
    # Campo 5 — estoque_minimo
    estoque_minimo = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Estoque Mínimo",
        help_text=(
            "Nível de segurança estabelecido para reposição (campo 5). "
            "None = não definido; não converta ausência em zero (RN02)."
        )
    )
    preco_referencia = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Preço de Referência (R$)",
        help_text=(
            "Custo unitário de referência para cálculo de valor em estoque. "
            "None = não informado; não converta ausência em R$ 0,00 (RN02)."
        )
    )
    descricao = models.TextField(blank=True, verbose_name="Observações / Descrição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['nome']

    def __str__(self) -> str:
        subtipo = f" · {self.tipo_item}" if self.tipo_item else ''
        return f"{self.nome}{subtipo} ({self.unidade})"

    @property
    def saldo_atual(self) -> Decimal:
        """
        Fórmula §6.1: Saldo = Σ Entradas − Σ Saídas.
        Retorna Decimal; nunca None (saldo zero é estado válido e auditável).
        """
        entradas = (
            self.movimentacoes
            .filter(tipo='ENTRADA')
            .aggregate(total=models.Sum('quantidade'))['total']
            or Decimal('0.00')
        )
        saidas = (
            self.movimentacoes
            .filter(tipo='SAIDA')
            .aggregate(total=models.Sum('quantidade'))['total']
            or Decimal('0.00')
        )
        return entradas - saidas

    @property
    def valor_total_estoque(self) -> Optional[Decimal]:
        """
        Valor financeiro do estoque atual.
        Retorna None quando o preço de referência não está informado (RN02).
        Nunca retorna zero por ausência de preço.
        """
        if self.preco_referencia is None:
            return None
        saldo = self.saldo_atual
        if saldo > Decimal('0.00'):
            return saldo * self.preco_referencia
        return Decimal('0.00')


class AtivoRural(models.Model):
    STATUS_MANUTENCAO = [
        ('OPERACIONAL', 'Operacional'),
        ('REVISAO', 'Revisão programada'),
        ('MANUTENCAO', 'Em manutenção'),
        ('INATIVO', 'Inativo'),
    ]
    UNIDADES_CONSUMO = [
        ('KM_L', 'km/L'),
        ('L_100KM', 'L/100 km'),
        ('L_H', 'L/h'),
    ]

    produto = models.OneToOneField(
        Produto, on_delete=models.CASCADE, related_name='cadastro_ativo',
        verbose_name='Veículo ou maquinário'
    )
    status_manutencao = models.CharField(
        max_length=20, choices=STATUS_MANUTENCAO, default='OPERACIONAL',
        verbose_name='Status de manutenção'
    )
    consumo_medio = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Consumo médio'
    )
    unidade_consumo = models.CharField(
        max_length=10, choices=UNIDADES_CONSUMO, blank=True,
        verbose_name='Unidade de consumo'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações de operação')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ativo Rural'
        verbose_name_plural = 'Ativos Rurais'
        ordering = ['produto__nome']

    def __str__(self) -> str:
        return f'{self.produto.tipo_item or self.produto.nome} — {self.produto.nome}'

    @property
    def ultima_movimentacao(self):
        return self.produto.movimentacoes.order_by('-data_movimentacao', '-id').first()


class ManutencaoAtivo(models.Model):
    TIPOS = [
        ('PREVENTIVA', 'Preventiva'),
        ('CORRETIVA', 'Corretiva'),
        ('REVISAO', 'Revisão'),
        ('PNEUS', 'Pneus e rodagem'),
        ('OUTRA', 'Outra'),
    ]

    ativo = models.ForeignKey(
        AtivoRural, on_delete=models.CASCADE, related_name='manutencoes',
        verbose_name='Ativo'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, default='PREVENTIVA')
    data = models.DateField(default=timezone.now, verbose_name='Data')
    descricao = models.CharField(max_length=180, verbose_name='Serviço realizado')
    odometro_km = models.DecimalField(
        max_digits=12, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.0'))], verbose_name='Odômetro (km)'
    )
    horimetro_h = models.DecimalField(
        max_digits=12, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.0'))], verbose_name='Horímetro (h)'
    )
    custo = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))], verbose_name='Custo (R$)'
    )
    fornecedor = models.CharField(max_length=150, blank=True, verbose_name='Oficina / fornecedor')
    responsavel = models.CharField(max_length=100, blank=True, verbose_name='Responsável')
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Manutenção de Ativo'
        verbose_name_plural = 'Manutenções de Ativos'
        ordering = ['-data', '-id']


# ---------------------------------------------------------------------------
# Lote de Insumo — rastreabilidade de lote/fabricante (campos 9 e 10)
# ---------------------------------------------------------------------------

class Lote(models.Model):
    """
    Lote de fabricante de um insumo para rastreamento de validade e saldo.

    Campos dos 13 oficiais armazenados aqui:
      campo 9  — lote (campo `numero_lote`)
      campo 10 — data_validade
    """

    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE,
        related_name='lotes', verbose_name="Produto"
    )
    # Campo 9 — lote
    numero_lote = models.CharField(
        max_length=60, verbose_name="Número do Lote",
        help_text="Código do lote do fabricante para rastreabilidade (campo 9)."
    )
    # Campo 10 — data_validade
    data_validade = models.DateField(
        null=True, blank=True, verbose_name="Data de Validade",
        help_text=(
            "Data de expiração do insumo perecível (campo 10). "
            "None = sem prazo de validade; não converta em data fictícia (RN02)."
        )
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lote de Insumo"
        verbose_name_plural = "Lotes de Insumo"
        unique_together = ('produto', 'numero_lote')
        ordering = ['data_validade', 'numero_lote']

    def __str__(self) -> str:
        return f"Lote {self.numero_lote} — {self.produto.nome}"

    @property
    def saldo_lote(self) -> Decimal:
        """Saldo específico deste lote: Σ Entradas − Σ Saídas filtradas por lote."""
        entradas = (
            self.movimentacoes
            .filter(tipo='ENTRADA')
            .aggregate(total=models.Sum('quantidade'))['total']
            or Decimal('0.00')
        )
        saidas = (
            self.movimentacoes
            .filter(tipo='SAIDA')
            .aggregate(total=models.Sum('quantidade'))['total']
            or Decimal('0.00')
        )
        return entradas - saidas


# ---------------------------------------------------------------------------
# Movimentacao — registro transacional com os 13 campos do regulamento
# ---------------------------------------------------------------------------

class Movimentacao(models.Model):
    """
    Registro de movimentação de insumo (entrada ou saída).
    Implementa todos os 13 campos oficiais do regulamento (RF01.2).
    Garante RN01.1 (bloqueio de saldo negativo) via clean().
    Campos opcionais são preservados como None (RN02).

    Campos dos 13 oficiais armazenados aqui:
      campo 4  — quantidade
      campo 6  — tipo_movimentacao (campo `tipo`)
      campo 7  — data_movimentacao
      campo 8  — preco_aquisicao (campo `preco_unitario`)
      campo 11 — fornecedor
      campo 12 — destino
      campo 13 — responsavel
    """

    TIPOS = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA',   'Saída'),
    ]

    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE,
        related_name='movimentacoes', verbose_name="Produto"
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movimentacoes', verbose_name="Lote do Fabricante"
    )
    # Campo 6 — tipo_movimentacao
    tipo = models.CharField(
        max_length=10, choices=TIPOS, verbose_name="Tipo de Movimentação",
        help_text="ENTRADA (compra/recebimento) ou SAÍDA (consumo/uso)."
    )
    # Campo 4 — quantidade
    quantidade = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Quantidade",
        help_text="Volume movimentado na unidade canônica do produto (campo 4)."
    )
    # Campo 7 — data_movimentacao
    data_movimentacao = models.DateField(
        default=timezone.now, verbose_name="Data da Movimentação",
        help_text="Data efetiva da operação (campo 7)."
    )
    odometro_km = models.DecimalField(
        max_digits=12, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.0'))],
        verbose_name="Leitura do odômetro (km)"
    )
    horimetro_h = models.DecimalField(
        max_digits=12, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.0'))],
        verbose_name="Leitura do horímetro (h)"
    )
    ativo = models.ForeignKey(
        AtivoRural, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimentacoes_insumos', verbose_name='Ativo relacionado'
    )
    ORIGENS_RECURSO = [
        ('COMPRA_EXTERNA', 'Compra externa'),
        ('PRODUCAO_PROPRIA', 'Produção própria'),
        ('TRANSFERENCIA_INTERNA', 'Transferência interna'),
    ]
    origem_recurso = models.CharField(
        max_length=24, choices=ORIGENS_RECURSO, default='COMPRA_EXTERNA',
        verbose_name='Origem do recurso'
    )
    # Campo 8 — preco_aquisicao (None preservado — RN02)
    preco_unitario = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Preço Unitário (R$)",
        help_text=(
            "Custo unitário pago na aquisição (campo 8 — preco_aquisicao). "
            "None = não informado; não converta em R$ 0,00 (RN02)."
        )
    )
    # Campo 11 — fornecedor
    fornecedor = models.CharField(
        max_length=150, blank=True, verbose_name="Fornecedor",
        help_text="Razão social ou nome fantasia do fornecedor (campo 11)."
    )
    comprador = models.CharField(
        max_length=100, blank=True, verbose_name="Comprador",
        help_text="Pessoa que realizou a compra ou contratação."
    )
    valor_total_pago = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Valor total pago (R$)",
        help_text="Valor total da compra. Deixe em branco se não informado."
    )
    # Campo 12 — destino
    destino = models.CharField(
        max_length=150, blank=True, verbose_name="Destino da Retirada",
        help_text="Setor, pasto, lote de animais ou talhão de uso/aplicação (campo 12)."
    )
    # Campo 13 — responsavel
    responsavel = models.CharField(
        max_length=100, blank=True, verbose_name="Responsável",
        help_text="Colaborador, operador ou Médico(a) Veterinário(a) encarregado(a) (campo 13)."
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ['-data_movimentacao', '-id']

    def clean(self) -> None:
        """
        RN01.1 — Bloqueio de Saldo Negativo.
        Impede saída que exceda o saldo disponível.
        Corrige contagem em edições de saídas existentes.
        """
        super().clean()
        if self.tipo == 'SAIDA' and self.quantidade is not None and getattr(self, 'produto_id', None):
            saldo_atual = self.produto.saldo_atual
            if self.pk:
                registro_anterior = Movimentacao.objects.filter(pk=self.pk).first()
                if registro_anterior and registro_anterior.tipo == 'SAIDA':
                    saldo_atual += registro_anterior.quantidade
            if self.quantidade > saldo_atual:
                raise ValidationError(
                    f"Operação não permitida (RN01.1): Saída de {self.quantidade} "
                    f"{self.produto.unidade} excede o saldo disponível "
                    f"({saldo_atual} {self.produto.unidade}). "
                    f"O sistema não permite saldo negativo."
                )

    def __str__(self) -> str:
        return (
            f"{self.get_tipo_display()} de {self.quantidade} {self.produto.unidade} "
            f"em {self.data_movimentacao.strftime('%d/%m/%Y')}"
        )


class TransferenciaRecurso(models.Model):
    ORIGENS = [
        ('COMPRA_EXTERNA', 'Adquirido externamente'),
        ('PRODUCAO_PROPRIA', 'Produzido na fazenda'),
        ('MISTO', 'Estoque de origem mista'),
    ]
    DESTINOS = [
        ('USO_INTERNO', 'Uso interno'),
        ('PRODUCAO_PROPRIA', 'Produção própria / transformação'),
    ]

    produto_origem = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name='transferencias_origem',
        verbose_name='Recurso de origem'
    )
    produto_destino = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name='transferencias_destino',
        verbose_name='Recurso de destino'
    )
    quantidade_origem = models.DecimalField(max_digits=12, decimal_places=2)
    quantidade_destino = models.DecimalField(max_digits=12, decimal_places=2)
    origem_recurso = models.CharField(max_length=24, choices=ORIGENS, verbose_name='Origem')
    destino_tipo = models.CharField(max_length=24, choices=DESTINOS, verbose_name='Destino')
    data = models.DateField(default=timezone.now)
    local_destino = models.CharField(max_length=150, blank=True, verbose_name='Setor / destino')
    responsavel = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)
    movimentacao_saida = models.OneToOneField(
        Movimentacao, on_delete=models.PROTECT, related_name='transferencia_saida'
    )
    movimentacao_entrada = models.OneToOneField(
        Movimentacao, on_delete=models.PROTECT, related_name='transferencia_entrada'
    )

    class Meta:
        verbose_name = 'Transferência de Recurso'
        verbose_name_plural = 'Transferências de Recursos'
        ordering = ['-data', '-id']

    def clean(self) -> None:
        super().clean()
        if self.produto_origem_id and self.produto_destino_id and self.produto_origem_id == self.produto_destino_id:
            raise ValidationError('A origem e o destino devem ser produtos diferentes.')


class PendenciaPrioritaria(models.Model):
    PRIORIDADES = [
        ('ALTA', 'Alta'),
        ('MEDIA', 'Média'),
        ('BAIXA', 'Baixa'),
    ]

    titulo = models.CharField(max_length=180, verbose_name='Pendência')
    descricao = models.TextField(blank=True, verbose_name='Descrição / ação necessária')
    prioridade = models.CharField(max_length=5, choices=PRIORIDADES, default='MEDIA')
    produto = models.ForeignKey(
        Produto, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pendencias', verbose_name='Insumo / recurso relacionado'
    )
    ativo = models.ForeignKey(
        AtivoRural, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pendencias', verbose_name='Veículo / ativo relacionado'
    )
    prazo = models.DateField(null=True, blank=True, verbose_name='Prazo')
    concluida = models.BooleanField(default=False, verbose_name='Concluída')
    criada_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pendência Prioritária'
        verbose_name_plural = 'Pendências Prioritárias'
        ordering = ['concluida', 'prazo', '-criada_em']

    def clean(self) -> None:
        super().clean()
        if self.ativo_id and self.produto_id and self.ativo.produto_id != self.produto_id:
            raise ValidationError('O produto relacionado deve corresponder ao ativo selecionado.')

    def __str__(self) -> str:
        return self.titulo


# ---------------------------------------------------------------------------
# LoteAnimais — rebanho bovino com ECC, pasto e suplementação (RF03.4)
# ---------------------------------------------------------------------------

class LoteAnimais(models.Model):
    """
    Lote de animais bovinos na propriedade (corte ou leite).

    Integrado ao motor analítico determinístico para:
    - Calcular o Consumo Diário Global do rebanho (§6.2)
    - Estimar a Autonomia de Estoque em Dias por lote (§6.3 — floor)
    - Gerar alertas semafóricos de suplementação no Dashboard (RF02.2)
    """

    CATEGORIAS = [
        ('CORTE',   'Gado de Corte'),
        ('LEITE',   'Gado de Leite'),
        ('CRIA',    'Cria / Bezerros'),
        ('RECRIA',  'Recria / Garrotes'),
        ('ENGORDA', 'Terminação / Engorda'),
    ]

    nome = models.CharField(
        max_length=120, unique=True, verbose_name="Identificação do Lote",
        help_text="Nome operacional do lote (ex: 'Lote 01 — Matrizes Nelore')."
    )
    categoria = models.CharField(
        max_length=40, choices=CATEGORIAS, default='CORTE',
        verbose_name="Categoria do Rebanho"
    )
    quantidade_cabecas = models.PositiveIntegerField(
        verbose_name="Quantidade de Cabeças",
        help_text="Número atual de animais no lote. Sincronizado via GTA (RF03.6)."
    )
    pasto_localizacao = models.CharField(
        max_length=120, verbose_name="Pasto / Localização",
        help_text="Identificação do pasto, curral ou setor onde o lote está alocado."
    )
    # ECC: Escore de Condição Corporal (escala zootécnica 1 a 5)
    escore_corporal = models.DecimalField(
        max_digits=3, decimal_places=1,
        default=Decimal('3.0'),
        verbose_name="Escore Corporal (ECC 1-5)",
        validators=[
            MinValueValidator(Decimal('1.0'), message="ECC mínimo é 1.0."),
            MaxValueValidator(Decimal('5.0'), message="ECC máximo é 5.0."),
        ],
        help_text="ECC: 1 (muito magro) a 5 (obeso). Avaliado pelo(a) Médico(a) Veterinário(a)."
    )
    peso_medio_estimado = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        verbose_name="Peso Médio Estimado (kg)",
        help_text="Peso médio dos animais. None = não avaliado (RN02)."
    )
    consumo_diario_cabeca = models.DecimalField(
        max_digits=8, decimal_places=3,
        default=Decimal('0.120'),
        verbose_name="Consumo Diário por Cabeça (kg/dia)",
        help_text="Quantidade de insumo suplementar por cabeça/dia (0.120 kg = 120 g sal mineral)."
    )
    insumo_suplementar = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lotes_consumidores',
        verbose_name="Insumo Suplementar Vinculado",
        help_text="Produto de suplementação principal. Usado para calcular autonomia de estoque."
    )
    observacoes = models.TextField(blank=True, verbose_name="Observações do Manejo")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lote de Animais"
        verbose_name_plural = "Lotes de Animais"
        ordering = ['nome']

    def __str__(self) -> str:
        return f"{self.nome} ({self.quantidade_cabecas} cab.) — {self.pasto_localizacao}"

    @property
    def consumo_diario_total_kg(self) -> Decimal:
        """
        Fórmula §6.2 — Parcela do Consumo Diário Global deste lote.
        Consumo Diário do Lote (kg/dia) = Cabeças × Consumo por Cabeça (kg/dia).
        """
        return Decimal(str(self.quantidade_cabecas)) * self.consumo_diario_cabeca

    def duracao_estimada_insumo(self, fator_seca: Decimal = Decimal('1.0')) -> Optional[int]:
        """
        Fórmula §6.3 — Autonomia de Estoque em Dias (floor) para este lote.
        Autonomia = ⌊ Saldo do Insumo / Consumo Diário Global do Lote ⌋

        Args:
            fator_seca: multiplicador de consumo para simulação sazonal.
                1.0 = período das águas (normal).
                2.0 = período de seca (pastagem degradada, consumo dobrado).

        Returns:
            int: dias de cobertura estimados (0 = esgotado).
            None: sem insumo vinculado ou consumo zero.
        """
        import math

        if not self.insumo_suplementar:
            return None

        saldo = self.insumo_suplementar.saldo_atual
        if saldo <= Decimal('0.00'):
            return 0

        # Normaliza para kg se necessário (saco = 30 kg)
        unidade = self.insumo_suplementar.unidade.lower()
        saldo_kg = saldo
        if 'sc' in unidade or 'saco' in unidade:
            saldo_kg = saldo * Decimal('30.0')

        consumo_dia = self.consumo_diario_total_kg * fator_seca
        if consumo_dia <= Decimal('0.00'):
            return None

        # §6.3: ⌊ Saldo / Consumo Diário ⌋ — floor conforme especificação do projeto
        return math.floor(float(saldo_kg / consumo_dia))

    def clean(self) -> None:
        """Valida ECC entre 1.0 e 5.0."""
        super().clean()
        if self.escore_corporal is not None:
            if not (Decimal('1.0') <= self.escore_corporal <= Decimal('5.0')):
                raise ValidationError(
                    "O Escore de Condição Corporal (ECC) deve estar entre 1.0 e 5.0."
                )


# ---------------------------------------------------------------------------
# CampanhaVacina — campanhas sanitárias obrigatórias IDARON (RF03.5)
# ---------------------------------------------------------------------------

class CampanhaVacina(models.Model):
    """
    Campanha oficial de vacinação obrigatória monitorada pelo IDARON
    (Instituto de Defesa Agropecuária e Florestal de Rondônia).

    Exemplos: Febre Aftosa (2x/ano), Brucelose (bezerras 3-8 meses), Raiva.

    Gera alertas 🔴 ALTA no Dashboard quando prazo_final <= 7 dias
    e a cobertura do rebanho ainda não atingiu a meta (especificação v3.0, RF02.2).
    """

    DOENCAS = [
        ('AFTOSA',     'Febre Aftosa'),
        ('BRUCELOSE',  'Brucelose Bovina'),
        ('RAIVA',      'Raiva dos Herbívoros'),
        ('CARBUNCULO', 'Carbúnculo Sintomático'),
        ('OUTRA',      'Outra Campanha Sanitária'),
    ]

    nome = models.CharField(
        max_length=120, verbose_name="Nome da Campanha",
        help_text="Ex: 'Vacinação Aftosa — 2ª Etapa 2026 — IDARON/RO'."
    )
    doenca = models.CharField(
        max_length=30, choices=DOENCAS, default='AFTOSA',
        verbose_name="Doença / Protocolo"
    )
    vacina_produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='campanhas_vacina',
        verbose_name="Vacina (Produto no Estoque)",
        help_text="Vacina vinculada. Ao registrar vacinação, as doses são abatidas do estoque."
    )
    data_inicio = models.DateField(
        verbose_name="Data de Início da Campanha",
        help_text="Abertura do período oficial de vacinação pelo IDARON."
    )
    prazo_final = models.DateField(
        verbose_name="Prazo Final (IDARON)",
        help_text="Data limite conforme calendário oficial do IDARON."
    )
    meta_cobertura_percentual = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('100.00'),
        verbose_name="Meta de Cobertura (%)",
        help_text="Percentual mínimo do rebanho que deve ser vacinado (padrão: 100%)."
    )
    observacoes = models.TextField(blank=True, verbose_name="Observações Sanitárias")
    ativa = models.BooleanField(
        default=True, verbose_name="Campanha Ativa",
        help_text="Campanhas encerradas são mantidas para auditoria histórica."
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Campanha de Vacinação"
        verbose_name_plural = "Campanhas de Vacinação"
        ordering = ['prazo_final', 'nome']

    def __str__(self) -> str:
        return f"{self.nome} (Prazo: {self.prazo_final.strftime('%d/%m/%Y')})"

    @property
    def dias_para_prazo(self) -> int:
        """Dias restantes até o prazo final da campanha."""
        return (self.prazo_final - date.today()).days

    @property
    def esta_vencida(self) -> bool:
        """True se o prazo final já passou."""
        return self.prazo_final < date.today()

    @property
    def total_doses_aplicadas(self) -> int:
        """Total de doses registradas em todos os lotes desta campanha."""
        return sum(r.doses_aplicadas for r in self.registros.all())

    def clean(self) -> None:
        """Valida que prazo_final >= data_inicio."""
        super().clean()
        if self.data_inicio and self.prazo_final:
            if self.prazo_final < self.data_inicio:
                raise ValidationError(
                    "O prazo final da campanha não pode ser anterior à data de início."
                )


# ---------------------------------------------------------------------------
# RegistroVacinacaoLote — aplicação por lote com abatimento de estoque (RF03.5)
# ---------------------------------------------------------------------------

class RegistroVacinacaoLote(models.Model):
    """
    Aplicação de vacina em um lote de animais dentro de uma campanha sanitária.

    Ao salvar (novo registro), gera automaticamente uma Movimentacao de SAÍDA
    no estoque da vacina vinculada à campanha, com rastreabilidade completa
    nos campos 12 (destino = lote vacinado) e 13 (responsavel = CRMV).
    """

    campanha = models.ForeignKey(
        CampanhaVacina,
        on_delete=models.CASCADE,
        related_name='registros',
        verbose_name="Campanha de Vacinação"
    )
    lote_animais = models.ForeignKey(
        LoteAnimais,
        on_delete=models.CASCADE,
        related_name='registros_vacinacao',
        verbose_name="Lote de Animais Vacinado"
    )
    data_aplicacao = models.DateField(
        default=date.today,
        verbose_name="Data de Aplicação"
    )
    doses_aplicadas = models.PositiveIntegerField(
        verbose_name="Doses Aplicadas",
        help_text="Quantidade de doses administradas neste lote nesta data."
    )
    # Campo 13 — responsavel (Médico(a) Veterinário(a) ou aplicador credenciado)
    responsavel = models.CharField(
        max_length=120, verbose_name="Responsável Técnico (CRMV)",
        help_text="Nome e CRMV do(a) Médico(a) Veterinário(a) responsável pela aplicação."
    )
    # Lote de vacina utilizado — rastreabilidade campos 9 e 10
    lote_vacina = models.ForeignKey(
        Lote,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='aplicacoes_vacinacao',
        verbose_name="Lote da Vacina (Fabricante)"
    )
    observacoes = models.TextField(blank=True, verbose_name="Observações da Vacinação")
    movimentacao_gerada = models.ForeignKey(
        Movimentacao,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='registro_vacinacao',
        verbose_name="Movimentação de Saída Gerada",
        help_text="Referência à Movimentacao de SAÍDA criada automaticamente no estoque."
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Vacinação por Lote"
        verbose_name_plural = "Registros de Vacinação por Lote"
        ordering = ['-data_aplicacao']

    def __str__(self) -> str:
        return (
            f"{self.campanha.doenca} — {self.lote_animais.nome} — "
            f"{self.doses_aplicadas} doses em {self.data_aplicacao.strftime('%d/%m/%Y')}"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Abate automático de doses no estoque ao registrar nova vacinação (RF03.5).
        Cria Movimentacao de SAÍDA com rastreabilidade dos campos 12 e 13.
        Respeita RN01.1: só cria movimentação se houver saldo suficiente.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.campanha.vacina_produto and not self.movimentacao_gerada:
            vacina = self.campanha.vacina_produto
            saldo_disponivel = vacina.saldo_atual
            doses_decimal = Decimal(str(self.doses_aplicadas))

            # RN01.1: verifica saldo antes de criar saída
            if doses_decimal <= saldo_disponivel:
                mov = Movimentacao.objects.create(
                    produto=vacina,
                    lote=self.lote_vacina,
                    tipo='SAIDA',
                    quantidade=doses_decimal,
                    data_movimentacao=self.data_aplicacao,
                    destino=f"Vacinação: {self.lote_animais.nome} ({self.campanha.nome})",
                    responsavel=self.responsavel,
                )
                # Atualiza referência cruzada sem trigger recursivo
                RegistroVacinacaoLote.objects.filter(pk=self.pk).update(movimentacao_gerada=mov)
                self.movimentacao_gerada = mov

    def clean(self) -> None:
        """Valida que doses_aplicadas > 0."""
        super().clean()
        if self.doses_aplicadas is not None and self.doses_aplicadas <= 0:
            raise ValidationError("O número de doses aplicadas deve ser maior que zero.")


# ---------------------------------------------------------------------------
# GuiaTransitoAnimal (GTA) — trânsito oficial do rebanho (RF03.6)
# ---------------------------------------------------------------------------

class GuiaTransitoAnimal(models.Model):
    """
    Guia de Trânsito Animal (GTA), documento obrigatório pelo IDARON
    para circulação de bovinos em Rondônia.

    Ao salvar (novo registro), atualiza automaticamente o campo
    `quantidade_cabecas` do LoteAnimais associado, mantendo o
    inventário físico do rebanho sincronizado (RF03.6).
    """

    TIPOS_MOVIMENTACAO = [
        ('ENTRADA', 'Entrada de Animais na Propriedade'),
        ('SAIDA',   'Saída de Animais da Propriedade'),
    ]

    FINALIDADES = [
        ('COMERCIO',      'Comercialização / Venda'),
        ('TRANSFERENCIA', 'Transferência Entre Propriedades'),
        ('EXPOSICAO',     'Exposição / Evento'),
        ('ABATE',         'Abate Direto'),
        ('REPRODUCAO',    'Reprodução / Inseminação'),
        ('OUTRA',         'Outra Finalidade'),
    ]

    numero_gta = models.CharField(
        max_length=30, unique=True,
        verbose_name="Número da GTA",
        help_text="Número único da Guia de Trânsito Animal emitida pelo IDARON."
    )
    tipo = models.CharField(
        max_length=10, choices=TIPOS_MOVIMENTACAO,
        verbose_name="Tipo de Movimentação"
    )
    lote_animais = models.ForeignKey(
        LoteAnimais,
        on_delete=models.CASCADE,
        related_name='gtas',
        verbose_name="Lote de Animais",
        help_text="Lote afetado. O saldo de cabeças é atualizado automaticamente ao salvar."
    )
    quantidade_animais = models.PositiveIntegerField(
        verbose_name="Quantidade de Animais",
        help_text="Número de animais transitados nesta GTA."
    )
    data_emissao = models.DateField(verbose_name="Data de Emissão da GTA")
    data_movimentacao = models.DateField(verbose_name="Data da Movimentação Efetiva")
    finalidade = models.CharField(
        max_length=20, choices=FINALIDADES, default='COMERCIO',
        verbose_name="Finalidade"
    )
    origem_destino = models.CharField(
        max_length=200, verbose_name="Propriedade de Origem / Destino",
        help_text=(
            "ENTRADA: nome e município de origem. "
            "SAÍDA: nome e município de destino."
        )
    )
    responsavel = models.CharField(max_length=120, verbose_name="Responsável / Transportador")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Guia de Trânsito Animal (GTA)"
        verbose_name_plural = "Guias de Trânsito Animal (GTA)"
        ordering = ['-data_movimentacao']

    def __str__(self) -> str:
        return (
            f"GTA {self.numero_gta} — {self.get_tipo_display()} de "
            f"{self.quantidade_animais} animal(is) — "
            f"{self.data_movimentacao.strftime('%d/%m/%Y')}"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Atualiza automaticamente quantidade_cabecas do lote ao registrar GTA:
        - ENTRADA: incrementa cabeças
        - SAÍDA: decrementa cabeças (nunca negativo — RN01.1)
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.lote_animais_id:
            lote = LoteAnimais.objects.get(pk=self.lote_animais_id)
            if self.tipo == 'ENTRADA':
                lote.quantidade_cabecas += self.quantidade_animais
            elif self.tipo == 'SAIDA':
                novo_total = lote.quantidade_cabecas - self.quantidade_animais
                lote.quantidade_cabecas = max(0, novo_total)  # RN01.1
            lote.save(update_fields=['quantidade_cabecas', 'atualizado_em'])

    def clean(self) -> None:
        """
        Valida regras da GTA:
        - quantidade_animais > 0
        - data_movimentacao >= data_emissao
        - SAÍDA não pode exceder saldo atual do lote (RN01.1)
        """
        super().clean()

        if self.quantidade_animais is not None and self.quantidade_animais <= 0:
            raise ValidationError(
                "A quantidade de animais na GTA deve ser maior que zero."
            )

        if self.data_emissao and self.data_movimentacao:
            if self.data_movimentacao < self.data_emissao:
                raise ValidationError(
                    "A data da movimentação efetiva não pode ser anterior à data de emissão da GTA."
                )

        if self.tipo == 'SAIDA' and self.lote_animais_id and self.quantidade_animais:
            lote = LoteAnimais.objects.filter(pk=self.lote_animais_id).first()
            if lote and self.quantidade_animais > lote.quantidade_cabecas:
                raise ValidationError(
                    f"Operação não permitida (RN01.1): Saída de {self.quantidade_animais} animais "
                    f"excede o saldo atual do lote ({lote.quantidade_cabecas} cabeças)."
                )
