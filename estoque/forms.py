from django import forms
from decimal import Decimal
from datetime import date
from .models import Produto, Lote, Movimentacao


class MovimentacaoForm(forms.ModelForm):
    """
    Formulário para registro manual de movimentações com validação rigorosa (RN01.1).
    """
    class Meta:
        model = Movimentacao
        fields = [
            'produto', 'tipo', 'quantidade', 'data_movimentacao',
            'preco_unitario', 'fornecedor', 'destino', 'responsavel'
        ]
        widgets = {
            'data_movimentacao': forms.DateInput(attrs={'type': 'date'}),
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
