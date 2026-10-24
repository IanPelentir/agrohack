from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from datetime import date, timedelta

from .models import Produto, Lote, Movimentacao
from .seed import popular_dados_demonstracao
from .analises import (
    calcular_estoque_critico,
    analisar_validade,
    estimar_duracao,
    detectar_anomalias,
    analisar_financeiro,
    gerar_alertas_priorizados
)


class BaseDadosDemonstracaoTestCase(TestCase):
    """
    Testes de integridade da base de demonstração e análises determinísticas.
    """

    def setUp(self):
        self.client = Client()
        popular_dados_demonstracao()

    def test_dados_ficticios_foram_carregados(self):
        """Verifica se produtos e movimentações foram inseridos corretamente."""
        self.assertGreater(Produto.objects.count(), 5)
        self.assertGreater(Movimentacao.objects.count(), 30)

    def test_estoque_critico_tebuconazol(self):
        """TA07: Fungicida com saldo 18 L (mínimo 50 L) deve gerar alerta ALTA."""
        fungicida = Produto.objects.get(nome="Fungicida Tebuconazol 200 EC")
        self.assertLessEqual(fungicida.saldo_atual, fungicida.estoque_minimo)
        alerta = calcular_estoque_critico(fungicida)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta['prioridade'], 'ALTA')
        self.assertIn("Estoque crítico", alerta['justificativa'])

    def test_alerta_validade_proxima_vacina(self):
        """TA08: Vacina com validade em 12 dias deve gerar alerta de perda/validade."""
        vacina = Produto.objects.get(nome="Vacina Antiaftosa Bivalente 50 Doses")
        alertas = analisar_validade(vacina)
        self.assertGreater(len(alertas), 0)
        self.assertIn(alertas[0]['prioridade'], ['ALTA', 'MEDIA'])

    def test_lote_vencido_oxitetraciclina(self):
        """Lote vencido com saldo remanescente deve gerar alerta ALTA."""
        oxitetra = Produto.objects.get(nome="Oxitetraciclina L.A. 200mg/ml 50ml")
        alertas = analisar_validade(oxitetra)
        self.assertGreater(len(alertas), 0)
        self.assertEqual(alertas[0]['prioridade'], 'ALTA')
        self.assertIn("vencido", alertas[0]['justificativa'].lower())

    def test_anomalia_diesel(self):
        """TA10: Saída de 1800 L de diesel em 1 dia deve ser detectada como anomalia."""
        diesel = Produto.objects.get(nome="Óleo Diesel S10 Granel")
        anomalia = detectar_anomalias(diesel)
        self.assertIsNotNone(anomalia)
        self.assertEqual(anomalia['prioridade'], 'MEDIA')
        self.assertIn("Saída atípica", anomalia['justificativa'])

    def test_excesso_capital_semente(self):
        """TA11: Semente com alto capital parado (> R$ 15k) deve gerar alerta de excesso."""
        semente = Produto.objects.get(nome="Semente Brachiaria brizantha cv. Marandu")
        alerta = analisar_financeiro(semente)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta['prioridade'], 'BAIXA')

    def test_historico_insuficiente_epi(self):
        """RN03: Produto com apenas 1 entrada não deve gerar previsão infundada."""
        epi = Produto.objects.get(nome="Respirador Facial com Filtro de Carvão Ativado 3M")
        estimativa = estimar_duracao(epi)
        self.assertIsNone(estimativa['dias'])
        self.assertFalse(estimativa['estimado'])

    def test_painel_renderiza_com_alertas_priorizados(self):
        """TA04/TA05: Painel principal deve exibir KPIs e lista ordenada de alertas."""
        response = self.client.get(reverse('estoque:painel'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'estoque/painel.html')
        self.assertContains(response, 'Fungicida Tebuconazol 200 EC')
        self.assertContains(response, 'Prioridade ALTA')

    def test_reanalise_automatica_apos_nova_movimentacao(self):
        """RF01.3 (TA03): Inserir nova saída deve recalcular saldos e alertas imediatamente."""
        sal = Produto.objects.get(nome="Sal Mineral Bovino 80 Fos 30kg")
        saldo_anterior = sal.saldo_atual

        # Registra saída de 60 sacos (deixando saldo em 20 sacos, abaixo do mínimo de 30 sacos)
        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': sal.id,
            'tipo': 'SAIDA',
            'quantidade': '60.00',
            'data': date.today().isoformat(),
            'destino': 'Uso emergencial',
            'responsavel': 'João Silva',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        sal.refresh_from_db()
        self.assertEqual(sal.saldo_atual, saldo_anterior - Decimal('60.00'))

        # Verifica se agora o Sal Mineral virou Estoque Crítico
        alerta_sal = calcular_estoque_critico(sal)
        self.assertIsNotNone(alerta_sal)
        self.assertEqual(alerta_sal['prioridade'], 'ALTA')

    def test_bloqueio_saldo_negativo_rn01_1(self):
        """RN01.1: Saída superior ao saldo atual disponível deve ser estritamente bloqueada."""
        sal = Produto.objects.get(nome="Sal Mineral Bovino 80 Fos 30kg")
        saldo_antes = sal.saldo_atual

        # Tenta retirar quantidade superior ao saldo atual (ex: saldo + 500 sacos)
        qtd_excessiva = saldo_antes + Decimal('500.00')
        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': sal.id,
            'tipo': 'SAIDA',
            'quantidade': str(qtd_excessiva),
            'data': date.today().isoformat(),
            'destino': 'Tentativa irregular',
            'responsavel': 'Operador Teste',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operação não permitida (RN01.1)')
        sal.refresh_from_db()
        # Garante que o saldo não foi alterado
        self.assertEqual(sal.saldo_atual, saldo_antes)

    def test_importacao_csv_previa_e_confirmacao_rf01(self):
        """RF01.1 / RF01.2: Ingestão de CSV com 13 campos, exibição de prévia e gravação atômica."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_content = (
            "produto,categoria,unidade,quantidade,tipo_movimentacao,data_movimentacao,estoque_minimo,preco_aquisicao,lote,data_validade,fornecedor,destino,responsavel\n"
            "Vermífugo Ivermectina 1%,Medicamentos,frasco,20.00,ENTRADA,2026-10-01,10.00,45.00,LT-IVM-01,2027-10-01,Vet Rondônia,Depósito,Dra. Bruna\n"
        ).encode('utf-8')

        arquivo_csv = SimpleUploadedFile("dados_teste.csv", csv_content, content_type="text/csv")

        # 1. Envio do CSV e conferência da prévia
        response_upload = self.client.post(reverse('estoque:importar'), {'arquivo_csv': arquivo_csv})
        self.assertEqual(response_upload.status_code, 200)
        self.assertContains(response_upload, 'Vermífugo Ivermectina 1%')
        self.assertContains(response_upload, 'Confirmar e Gravar Registros')

        # 2. Confirmação e gravação atômica
        response_confirmar = self.client.post(reverse('estoque:confirmar_importacao'), follow=True)
        self.assertEqual(response_confirmar.status_code, 200)
        self.assertContains(response_confirmar, 'Importação concluída com sucesso')

        # 3. Verifica no banco se o produto, lote e saldo foram registrados
        prod = Produto.objects.filter(nome="Vermífugo Ivermectina 1%").first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.unidade, 'frasco')
        self.assertEqual(prod.saldo_atual, Decimal('20.00'))
        self.assertEqual(prod.lotes.count(), 1)
        self.assertEqual(prod.lotes.first().numero_lote, 'LT-IVM-01')

    def test_conflito_unidades_csv_rn01(self):
        """RN01: Se produto já existir com unidade diferente, linha deve ser marcada como inválida."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Tebuconazol já existe no banco com unidade 'L'
        csv_conflito = (
            "produto,categoria,unidade,quantidade,tipo_movimentacao,data_movimentacao\n"
            "Fungicida Tebuconazol 200 EC,Defensivos,kg,10.00,ENTRADA,2026-10-01\n"
        ).encode('utf-8')

        arquivo_csv = SimpleUploadedFile("conflito.csv", csv_conflito, content_type="text/csv")
        response = self.client.post(reverse('estoque:importar'), {'arquivo_csv': arquivo_csv})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Conflito de unidade (RN01)')

    def test_ruptura_imediata_saldo_zerado_sem_minimo_rf03_1(self):
        """RF03.1: Produto zerado ou negativo deve gerar alerta de ruptura crítica mesmo sem estoque mínimo."""
        p_zerado = Produto.objects.create(
            nome="Adjuvante Espalhante Adesivo",
            categoria="DEFENSIVOS",
            unidade="L",
            estoque_minimo=None  # Sem estoque mínimo cadastrado
        )
        self.assertEqual(p_zerado.saldo_atual, Decimal('0.00'))

        alerta = calcular_estoque_critico(p_zerado)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta['prioridade'], 'ALTA')
        self.assertIn("zerado ou negativo", alerta['justificativa'].lower())

    def test_agrogado_lotes_gado_metricas_regionais(self):
        """Valida se o painel exibe total de cabeças, cotação regional de Ariquemes e lotes de gado."""
        response = self.client.get(reverse('estoque:painel'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('lotes_animais', response.context)
        self.assertGreater(len(response.context['lotes_animais']), 0)
        self.assertEqual(response.context['kpis']['total_cabecas'], 460)
        self.assertEqual(response.context['kpis']['cotacao_arroba'], Decimal('228.50'))
        self.assertContains(response, 'Lote 01 - Garrotes Nelore')
        self.assertContains(response, 'Ariquemes / RO')

    def test_simulacao_sazonal_inicio_seca(self):
        """Valida ativação do modo seca (?seca=1), gerando alerta sazonal e acelerando consumo."""
        response = self.client.get(reverse('estoque:painel') + '?seca=1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['modo_seca'])
        self.assertContains(response, 'Transição para Época de Seca')
        lote1 = next(l for l in response.context['lotes_animais'] if 'Lote 01' in l['nome'])
        self.assertEqual(lote1['consumo_diario_cabeca_g'], 240)  # 120g * 2 na seca

