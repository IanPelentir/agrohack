from django import forms
from decimal import Decimal
from datetime import date
from .models import (
    AtivoRural,
    ManutencaoAtivo,
    PendenciaPrioritaria,
    Produto,
    Lote,
    Movimentacao,
    TransferenciaRecurso,
)


class ProdutoForm(forms.ModelForm):
    tipo_item = forms.CharField(
        label='Tipo específico',
        max_length=100,
        help_text='Digite livremente: caminhonete, trator, óleo 15W40, chave de roda, sal mineral...',
        widget=forms.TextInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Ex: caminhonete, trator, óleo hidráulico, chave de roda',
            'list': 'sugestoes-tipo-item',
        }),
    )

    class Meta:
        model = Produto
        fields = [
            'nome', 'categoria', 'tipo_item', 'unidade', 'tipo_embalagem', 'embalagem_em_caixa',
            'peso_embalagem_kg', 'volume_embalagem_ml', 'fabricante', 'modelo',
            'numero_serie', 'placa', 'chassi', 'ano_fabricacao', 'estoque_minimo',
            'preco_referencia', 'descricao',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'categoria': forms.Select(attrs={'class': 'form-control-custom'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'kg, L, frasco, un'}),
            'tipo_embalagem': forms.Select(attrs={'class': 'form-control-custom'}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'placa': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Ex: ABC1D23'}),
            'chassi': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Número do chassi'}),
            'peso_embalagem_kg': forms.NumberInput(attrs={'class': 'form-control-custom', 'step': '0.001', 'min': '0'}),
            'volume_embalagem_ml': forms.NumberInput(attrs={'class': 'form-control-custom', 'step': '0.01', 'min': '0'}),
            'ano_fabricacao': forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '1900', 'max': '2100'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control-custom', 'step': '0.01', 'min': '0'}),
            'preco_referencia': forms.NumberInput(attrs={'class': 'form-control-custom', 'step': '0.01', 'min': '0'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3}),
            'embalagem_em_caixa': forms.CheckboxInput(attrs={'class': 'form-control-custom'}),
        }


class MovimentacaoForm(forms.ModelForm):
    """
    Formulário para registro manual de movimentações com validação rigorosa (RN01.1).
    """
    class Meta:
        model = Movimentacao
        fields = [
            'produto', 'tipo', 'quantidade', 'data_movimentacao',
            'odometro_km', 'horimetro_h', 'ativo', 'origem_recurso',
            'preco_unitario', 'valor_total_pago', 'fornecedor', 'comprador',
            'destino', 'responsavel'
        ]
        widgets = {
            'data_movimentacao': forms.DateInput(attrs={'type': 'date'}),
            'odometro_km': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'horimetro_h': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'ativo': forms.Select(attrs={'class': 'form-control-custom'}),
            'origem_recurso': forms.Select(attrs={'class': 'form-control-custom'}),
        }

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        if quantidade is not None and quantidade <= Decimal('0.00'):
            raise forms.ValidationError("A quantidade movimentada deve ser estritamente maior que zero.")
        return quantidade

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        tipo = cleaned_data.get('tipo')
        quantidade = cleaned_data.get('quantidade')

        # RN01.1 - Bloqueio de Saldo Negativo
        if produto and tipo == 'SAIDA' and quantidade:
            saldo_disponivel = produto.saldo_atual
            if quantidade > saldo_disponivel:
                raise forms.ValidationError(
                    f"Operação não permitida (RN01.1): A quantidade de saída solicitada ({quantidade} {produto.unidade}) "
                    f"excede o saldo disponível em estoque ({saldo_disponivel} {produto.unidade})."
                )
        return cleaned_data


class UploadCSVForm(forms.Form):
    """
    Formulário para validação do arquivo CSV de importação oficial (RF01.1).
    """
    arquivo_csv = forms.FileField(
        label="Arquivo CSV",
        help_text="Selecione um arquivo .csv delimitado por vírgula ou ponto-e-vírgula (UTF-8 ou ISO-8859-1)"
    )

    def clean_arquivo_csv(self):
        arquivo = self.cleaned_data.get('arquivo_csv')
        if arquivo:
            nome = arquivo.name.lower()
            if not nome.endswith('.csv'):
                raise forms.ValidationError("Formato de arquivo inválido. Apenas arquivos .csv são suportados.")
            if arquivo.size > 10 * 1024 * 1024:  # 10 MB
                raise forms.ValidationError("O arquivo excede o limite máximo de 10 MB.")
        return arquivo


from .models import Produto, Lote, Movimentacao, LoteAnimais


class LoteAnimaisForm(forms.ModelForm):
    """Formulário amigável para cadastro e edição rápida de Lote de Gado."""
    class Meta:
        model = LoteAnimais
        fields = [
            'nome', 'categoria', 'quantidade_cabecas', 'pasto_localizacao',
            'escore_corporal', 'peso_medio_estimado', 'consumo_diario_cabeca',
            'insumo_suplementar', 'observacoes'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lote 05 - Garrotes Nelore'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'quantidade_cabecas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Ex: 120'}),
            'pasto_localizacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Piquete 05 (Brachiaria)'}),
            'escore_corporal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '1.0', 'max': '5.0', 'placeholder': 'Ex: 3.2'}),
            'peso_medio_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ex: 380.00'}),
            'consumo_diario_cabeca': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': 'Ex: 0.120'}),
            'insumo_suplementar': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações do manejo ou saúde do lote'}),
        }


class AtivoRuralForm(forms.ModelForm):
    class Meta:
        model = AtivoRural
        fields = ['status_manutencao', 'consumo_medio', 'unidade_consumo', 'observacoes']
        widgets = {
            'status_manutencao': forms.Select(attrs={'class': 'form-control-custom'}),
            'consumo_medio': forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '0.01', 'step': '0.01'}),
            'unidade_consumo': forms.Select(attrs={'class': 'form-control-custom'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('consumo_medio') and not cleaned_data.get('unidade_consumo'):
            self.add_error('unidade_consumo', 'Informe a unidade do consumo médio.')
        return cleaned_data


class ManutencaoAtivoForm(forms.ModelForm):
    class Meta:
        model = ManutencaoAtivo
        fields = [
            'ativo', 'tipo', 'data', 'descricao', 'odometro_km', 'horimetro_h',
            'custo', 'fornecedor', 'responsavel', 'observacoes',
        ]
        widgets = {
            'ativo': forms.Select(attrs={'class': 'form-control-custom'}),
            'tipo': forms.Select(attrs={'class': 'form-control-custom'}),
            'data': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'odometro_km': forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '0', 'step': '0.1'}),
            'horimetro_h': forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '0', 'step': '0.1'}),
            'custo': forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '0', 'step': '0.01'}),
            'fornecedor': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control-custom'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ativo'].queryset = AtivoRural.objects.select_related('produto').all()


class TransferenciaRecursoForm(forms.Form):
    produto_origem = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True), label='Recurso de origem',
        widget=forms.Select(attrs={'class': 'form-control-custom'})
    )
    quantidade_origem = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
        label='Quantidade utilizada na origem',
        widget=forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '0.01', 'step': '0.01'})
    )
    produto_destino = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True), label='Recurso produzido / destino',
        widget=forms.Select(attrs={'class': 'form-control-custom'})
    )
    quantidade_destino = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
        label='Quantidade gerada no destino',
        widget=forms.NumberInput(attrs={'class': 'form-control-custom', 'min': '0.01', 'step': '0.01'})
    )
    origem_recurso = forms.ChoiceField(
        choices=TransferenciaRecurso.ORIGENS, label='Origem do recurso utilizado',
        widget=forms.Select(attrs={'class': 'form-control-custom'})
    )
    destino_tipo = forms.ChoiceField(
        choices=TransferenciaRecurso.DESTINOS, label='Finalidade do destino',
        widget=forms.Select(attrs={'class': 'form-control-custom'})
    )
    data = forms.DateField(
        label='Data', widget=forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'})
    )
    local_destino = forms.CharField(
        max_length=150, required=False, label='Setor / lote / destino interno',
        widget=forms.TextInput(attrs={'class': 'form-control-custom'})
    )
    responsavel = forms.CharField(
        max_length=100, required=False, label='Responsável',
        widget=forms.TextInput(attrs={'class': 'form-control-custom'})
    )
    observacoes = forms.CharField(
        required=False, label='Descrição da conversão',
        widget=forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 2})
    )

    def clean(self):
        cleaned_data = super().clean()
        origem = cleaned_data.get('produto_origem')
        destino = cleaned_data.get('produto_destino')
        quantidade_origem = cleaned_data.get('quantidade_origem')
        if origem and destino and origem == destino:
            self.add_error('produto_destino', 'Escolha um produto diferente para o destino.')
        if origem and quantidade_origem and quantidade_origem > origem.saldo_atual:
            self.add_error(
                'quantidade_origem',
                f'Saldo disponível: {origem.saldo_atual} {origem.unidade}.'
            )
        return cleaned_data


class PendenciaPrioritariaForm(forms.ModelForm):
    class Meta:
        model = PendenciaPrioritaria
        fields = ['titulo', 'descricao', 'prioridade', 'produto', 'ativo', 'prazo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Ex: Repor diesel do tanque principal'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 2, 'placeholder': 'Ação ou contexto necessário'}),
            'prioridade': forms.Select(attrs={'class': 'form-control-custom'}),
            'produto': forms.Select(attrs={'class': 'form-control-custom'}),
            'ativo': forms.Select(attrs={'class': 'form-control-custom'}),
            'prazo': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].required = False
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True)
        self.fields['ativo'].required = False
        self.fields['ativo'].queryset = AtivoRural.objects.select_related('produto').all()
