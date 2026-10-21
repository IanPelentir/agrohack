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
