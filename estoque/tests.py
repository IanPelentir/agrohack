from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from datetime import date, timedelta

from .models import (
    AtivoRural,
    Lote,
    LoteAnimais,
    ManutencaoAtivo,
    Movimentacao,
    MortalidadeAnimal,
    PendenciaPrioritaria,
    Produto,
    TransferenciaRecurso,
)
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

    def test_movimentacao_cadastra_novo_produto_com_entrada_inicial(self):
        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': '__novo__',
            'tipo': 'ENTRADA',
            'quantidade': '18.50',
            'data_movimentacao': date.today().isoformat(),
            'novo_produto-nome': 'Produto criado na entrada',
            'novo_produto-categoria': 'INSUMOS',
            'novo_produto-tipo_item': 'Adubo orgânico',
            'novo_produto-unidade': 'kg',
            'preco_unitario': '4.20',
        })

        self.assertRedirects(response, reverse('estoque:painel'))
        produto = Produto.objects.get(nome='Produto criado na entrada')
        self.assertEqual(produto.saldo_atual, Decimal('18.50'))
        self.assertEqual(produto.movimentacoes.count(), 1)
        self.assertEqual(produto.movimentacoes.first().preco_unitario, Decimal('4.20'))

    def test_entrada_invalida_nao_salva_novo_produto(self):
        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': '__novo__',
            'tipo': 'ENTRADA',
            'quantidade': 'invalida',
            'data_movimentacao': date.today().isoformat(),
            'novo_produto-nome': 'Produto não deve ficar órfão',
            'novo_produto-categoria': 'INSUMOS',
            'novo_produto-tipo_item': '',
            'novo_produto-unidade': 'kg',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Produto.objects.filter(nome='Produto não deve ficar órfão').exists())

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

    def test_registrar_mortalidade_reduz_lote_e_preserva_historico(self):
        lote = LoteAnimais.objects.create(
            nome='Lote mortalidade teste', categoria='CRIA', quantidade_cabecas=8,
            pasto_localizacao='Piquete teste',
        )

        response = self.client.post(reverse('estoque:lote_mortalidade', args=[lote.pk]), {
            'categoria_animal': 'BEZERRO',
            'quantidade': '2',
            'data': date.today().isoformat(),
            'causa': 'Doença',
            'responsavel': 'Veterinária teste',
        })

        self.assertRedirects(response, reverse('estoque:lote_mortalidade', args=[lote.pk]))
        lote.refresh_from_db()
        self.assertEqual(lote.quantidade_cabecas, 6)
        ocorrencia = MortalidadeAnimal.objects.get(lote_animais=lote)
        self.assertEqual(ocorrencia.quantidade, 2)
        self.assertEqual(ocorrencia.categoria_animal, 'BEZERRO')

    def test_mortalidade_nao_pode_exceder_cabecas_do_lote(self):
        lote = LoteAnimais.objects.create(
            nome='Lote limite mortalidade', categoria='CORTE', quantidade_cabecas=2,
            pasto_localizacao='Piquete teste',
        )

        response = self.client.post(reverse('estoque:lote_mortalidade', args=[lote.pk]), {
            'categoria_animal': 'VACA',
            'quantidade': '3',
            'data': date.today().isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'O lote possui apenas 2 cabeça(s) disponível(is).')
        lote.refresh_from_db()
        self.assertEqual(lote.quantidade_cabecas, 2)
        self.assertFalse(MortalidadeAnimal.objects.filter(lote_animais=lote).exists())

    def test_cadastro_produto_maquina_com_identificacao(self):
        response_form = self.client.get(reverse('estoque:produto_novo'))
        self.assertEqual(response_form.status_code, 200)
        self.assertContains(response_form, 'Máquinas e Implementos Agrícolas')
        self.assertContains(response_form, 'data-product-group="VEICULO"')
        self.assertContains(response_form, 'data-package-kind="SACO"')

        response = self.client.post(reverse('estoque:produto_novo'), {
            'nome': 'Trator Fazenda Teste',
            'categoria': 'MAQUINAS',
            'tipo_item': 'Trator agrícola',
            'unidade': 'un',
            'tipo_embalagem': 'UNIDADE',
            'fabricante': 'Agrícola Teste',
            'modelo': 'TR-100',
            'numero_serie': 'PAT-2026-001',
            'ano_fabricacao': '2024',
            'estoque_minimo': '',
            'preco_referencia': '185000.00',
            'descricao': 'Trator para manejo e transporte na fazenda.',
        })

        self.assertEqual(response.status_code, 302)
        trator = Produto.objects.get(nome='Trator Fazenda Teste')
        self.assertEqual(trator.categoria, 'MAQUINAS')
        self.assertEqual(trator.numero_serie, 'PAT-2026-001')
        self.assertEqual(trator.ano_fabricacao, 2024)

        response_movimentacao = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': trator.id,
            'tipo': 'ENTRADA',
            'quantidade': '1',
            'data_movimentacao': date.today().isoformat(),
            'horimetro_h': '1380.5',
        })
        self.assertEqual(response_movimentacao.status_code, 302)
        entrada = Movimentacao.objects.get(produto=trator, tipo='ENTRADA')
        self.assertEqual(entrada.horimetro_h, Decimal('1380.5'))

        response_detalhe = self.client.get(reverse('estoque:produto_detalhe', args=[trator.id]))
        self.assertEqual(response_detalhe.status_code, 200)
        self.assertContains(response_detalhe, 'Sem caixa')
        self.assertContains(response_detalhe, 'PAT-2026-001')

    def test_produto_pode_ser_cadastrado_sem_tipo_especifico(self):
        response = self.client.post(reverse('estoque:produto_novo'), {
            'nome': 'Item sem tipo específico',
            'categoria': 'OUTROS',
            'unidade': 'un',
            'tipo_embalagem': 'UNIDADE',
        })

        self.assertEqual(response.status_code, 302)
        produto = Produto.objects.get(nome='Item sem tipo específico')
        self.assertEqual(produto.tipo_item, '')

    def test_editar_produto_preserva_movimentacoes(self):
        produto = Produto.objects.create(
            nome='Produto para editar', categoria='INSUMOS', unidade='kg'
        )
        movimentacao = Movimentacao.objects.create(
            produto=produto, tipo='ENTRADA', quantidade=Decimal('5'),
            data_movimentacao=date.today(),
        )

        response = self.client.post(
            reverse('estoque:produto_editar', args=[produto.pk]),
            {
                'nome': 'Produto editado',
                'categoria': 'INSUMOS',
                'unidade': 'kg',
                'tipo_embalagem': 'UNIDADE',
            },
        )

        self.assertRedirects(response, reverse('estoque:produto_detalhe', args=[produto.pk]))
        produto.refresh_from_db()
        self.assertEqual(produto.nome, 'Produto editado')
        self.assertTrue(Movimentacao.objects.filter(pk=movimentacao.pk).exists())

    def test_desativar_produto_preserva_historico_e_remove_da_lista(self):
        produto = Produto.objects.create(
            nome='Produto para desativar', categoria='INSUMOS', unidade='kg'
        )
        movimentacao = Movimentacao.objects.create(
            produto=produto, tipo='ENTRADA', quantidade=Decimal('3'),
            data_movimentacao=date.today(),
        )

        response = self.client.post(reverse('estoque:produto_excluir', args=[produto.pk]))

        self.assertRedirects(response, reverse('estoque:produto_lista'))
        produto.refresh_from_db()
        self.assertFalse(produto.ativo)
        self.assertTrue(Movimentacao.objects.filter(pk=movimentacao.pk).exists())
        self.assertNotContains(self.client.get(reverse('estoque:produto_lista')), produto.nome)

    def test_cadastro_e_movimentacao_de_veiculo(self):
        response = self.client.post(reverse('estoque:produto_novo'), {
            'nome': 'Caminhonete Teste da Fazenda',
            'categoria': 'VEICULOS',
            'tipo_item': 'Caminhonete 4x4',
            'unidade': 'un',
            'tipo_embalagem': 'UNIDADE',
            'fabricante': 'Toyota',
            'modelo': 'Hilux CD 4x4',
            'ano_fabricacao': '2022',
            'placa': 'ABC1D23',
            'chassi': '9BR00000000000001',
            'estoque_minimo': '1',
            'preco_referencia': '190000',
        })

        self.assertEqual(response.status_code, 302)
        veiculo = Produto.objects.get(nome='Caminhonete Teste da Fazenda')
        self.assertEqual(veiculo.placa, 'ABC1D23')
        self.assertEqual(veiculo.chassi, '9BR00000000000001')

        response_movimentacao = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': veiculo.id,
            'tipo': 'ENTRADA',
            'quantidade': '1',
            'data_movimentacao': date.today().isoformat(),
            'odometro_km': '45210.5',
        })
        self.assertEqual(response_movimentacao.status_code, 302)
        entrada = Movimentacao.objects.get(produto=veiculo, tipo='ENTRADA')
        self.assertEqual(entrada.odometro_km, Decimal('45210.5'))

    def test_base_demo_inclui_ativos_da_fazenda(self):
        self.assertTrue(Produto.objects.filter(categoria='MAQUINAS').exists())
        self.assertTrue(Produto.objects.filter(categoria='VEICULOS').exists())
        self.assertTrue(Produto.objects.filter(categoria='FERRAMENTAS', tipo_item='Motosserra').exists())
        self.assertTrue(Produto.objects.filter(categoria='COMBUSTIVEIS', tipo_item='Óleo de motor 15W40').exists())

    def test_busca_catalogo_por_tipo_especifico(self):
        response = self.client.get(reverse('estoque:produto_lista'), {'busca': 'Óleo de motor 15W40'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['produtos']), 1)
        self.assertEqual(response.context['produtos'][0]['tipo_item'], 'Óleo de motor 15W40')

    def test_filtro_categoria_exibe_descricao_e_filtra_codigo(self):
        response = self.client.get(
            reverse('estoque:produto_lista'), {'categoria': 'VEICULOS'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="VEICULOS"')
        self.assertContains(response, 'Veículos e Automóveis Rurais')
        self.assertTrue(response.context['produtos'])
        self.assertTrue(all(p['categoria'] == 'Veículos e Automóveis Rurais' for p in response.context['produtos']))

    def test_compra_registra_comprador_valor_e_data(self):
        produto = Produto.objects.create(
            nome='Ração Teste', categoria='SUPLEMENTOS', unidade='saco'
        )
        data_compra = date(2026, 10, 20)
        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': produto.id,
            'tipo': 'ENTRADA',
            'quantidade': '12',
            'data_movimentacao': data_compra.isoformat(),
            'preco_unitario': '95.00',
            'valor_total_pago': '1080.00',
            'fornecedor': 'Cooperativa Teste',
            'comprador': 'Ana Compras',
        })

        self.assertEqual(response.status_code, 302)
        compra = Movimentacao.objects.get(produto=produto, tipo='ENTRADA')
        self.assertEqual(compra.data_movimentacao, data_compra)
        self.assertEqual(compra.comprador, 'Ana Compras')
        self.assertEqual(compra.valor_total_pago, Decimal('1080.00'))

    def test_formulario_movimentacao_exibe_dados_do_produto(self):
        trator = Produto.objects.create(
            nome='Trator do Formulário', categoria='MAQUINAS', unidade='un',
            fabricante='Marca Rural', modelo='TR-200', numero_serie='PAT-55',
        )
        racao = Produto.objects.create(
            nome='Ração do Formulário', categoria='SUPLEMENTOS', unidade='saco',
            tipo_embalagem='SACO', peso_embalagem_kg=Decimal('30.000'),
        )

        response = self.client.get(reverse('estoque:movimentacao_nova'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-categoria="MAQUINAS"')
        self.assertContains(response, 'data-categoria="SUPLEMENTOS"')
        self.assertContains(response, 'data-serie="PAT-55"')
        self.assertContains(response, 'data-peso="30,000"')
        ids_produtos = {produto['id'] for produto in response.context['produtos']}
        self.assertIn(trator.id, ids_produtos)
        self.assertIn(racao.id, ids_produtos)

    def test_quantidade_de_ativo_deve_ser_inteira(self):
        trator = Produto.objects.create(
            nome='Trator Fracionado', categoria='MAQUINAS', unidade='un'
        )
        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': trator.id,
            'tipo': 'ENTRADA',
            'quantidade': '1.5',
            'data_movimentacao': date.today().isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'controlados por unidade inteira')
        self.assertFalse(Movimentacao.objects.filter(produto=trator).exists())

        ferramenta = Produto.objects.create(
            nome='Chave de roda teste', categoria='FERRAMENTAS',
            tipo_item='Chave de roda', unidade='un'
        )
        response_ferramenta = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': ferramenta.id,
            'tipo': 'ENTRADA',
            'quantidade': '1.5',
            'data_movimentacao': date.today().isoformat(),
        })

        self.assertEqual(response_ferramenta.status_code, 200)
        self.assertContains(response_ferramenta, 'controlados por unidade inteira')
        self.assertFalse(Movimentacao.objects.filter(produto=ferramenta).exists())

    def test_saida_rastreavel_registra_lote_consumido(self):
        medicamento = Produto.objects.create(
            nome='Medicamento com Lote Teste', categoria='MEDICAMENTOS', unidade='frasco'
        )
        lote = Lote.objects.create(produto=medicamento, numero_lote='LT-MED-01')
        Movimentacao.objects.create(
            produto=medicamento, lote=lote, tipo='ENTRADA', quantidade=Decimal('2.00')
        )

        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': medicamento.id,
            'tipo': 'SAIDA',
            'quantidade': '1',
            'data_movimentacao': date.today().isoformat(),
            'lote': 'LT-MED-01',
        })

        self.assertEqual(response.status_code, 302)
        saida = Movimentacao.objects.get(produto=medicamento, tipo='SAIDA')
        self.assertEqual(saida.lote, lote)

    def test_saida_nao_cria_lote_inexistente(self):
        medicamento = Produto.objects.create(
            nome='Medicamento sem Lote Teste', categoria='MEDICAMENTOS', unidade='frasco'
        )
        Movimentacao.objects.create(
            produto=medicamento, tipo='ENTRADA', quantidade=Decimal('2.00')
        )

        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': medicamento.id,
            'tipo': 'SAIDA',
            'quantidade': '1',
            'data_movimentacao': date.today().isoformat(),
            'lote': 'LT-NAO-CADASTRADO',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'não pode ser usado em uma saída')
        self.assertFalse(Lote.objects.filter(produto=medicamento).exists())

    def test_pagina_recursos_exibe_frota_e_producao(self):
        response = self.client.get(reverse('estoque:recursos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recursos e Produção da Fazenda')
        self.assertContains(response, 'Caminhonete Toyota Hilux - Frota 01')
        self.assertContains(response, 'Converter ou destinar recurso')
        self.assertTrue(AtivoRural.objects.filter(produto__categoria='VEICULOS').exists())

    def test_atualizar_status_e_consumo_do_ativo(self):
        veiculo = Produto.objects.get(nome='Caminhonete Toyota Hilux - Frota 01')
        ativo, _ = AtivoRural.objects.get_or_create(produto=veiculo)

        response = self.client.post(reverse('estoque:ativo_atualizar', args=[ativo.id]), {
            'status_manutencao': 'REVISAO',
            'consumo_medio': '8.50',
            'unidade_consumo': 'KM_L',
            'observacoes': 'Revisão por quilometragem.',
        })

        self.assertEqual(response.status_code, 302)
        ativo.refresh_from_db()
        self.assertEqual(ativo.status_manutencao, 'REVISAO')
        self.assertEqual(ativo.consumo_medio, Decimal('8.50'))

    def test_registrar_manutencao_do_ativo(self):
        trator = Produto.objects.get(nome='Trator Massey Ferguson MF 4275 - TR-001')
        ativo, _ = AtivoRural.objects.get_or_create(produto=trator)
        ativo.status_manutencao = 'MANUTENCAO'
        ativo.save()

        response = self.client.post(reverse('estoque:manutencao_nova'), {
            'ativo': ativo.id,
            'tipo': 'PREVENTIVA',
            'data': date.today().isoformat(),
            'descricao': 'Troca de óleo e filtros',
            'horimetro_h': '1300.5',
            'custo': '850.00',
            'fornecedor': 'Oficina Rural',
            'responsavel': 'Mecânico da fazenda',
        })

        self.assertEqual(response.status_code, 302)
        manutencao = ManutencaoAtivo.objects.get(ativo=ativo, descricao='Troca de óleo e filtros')
        self.assertEqual(manutencao.horimetro_h, Decimal('1300.5'))
        ativo.refresh_from_db()
        self.assertEqual(ativo.status_manutencao, 'OPERACIONAL')

    def test_vincular_insumo_operacional_a_veiculo(self):
        veiculo = Produto.objects.get(nome='Caminhonete Toyota Hilux - Frota 01')
        ativo, _ = AtivoRural.objects.get_or_create(produto=veiculo)
        diesel = Produto.objects.get(nome='Óleo Diesel S10 Granel')

        response = self.client.post(reverse('estoque:movimentacao_nova'), {
            'produto': diesel.id,
            'tipo': 'ENTRADA',
            'quantidade': '40',
            'data_movimentacao': date.today().isoformat(),
            'ativo': ativo.id,
            'origem_recurso': 'COMPRA_EXTERNA',
        })

        self.assertEqual(response.status_code, 302)
        movimento = Movimentacao.objects.get(produto=diesel, ativo=ativo, tipo='ENTRADA')
        self.assertEqual(movimento.origem_recurso, 'COMPRA_EXTERNA')

    def test_transferir_producao_interna_com_conversao_de_unidades(self):
        milho = Produto.objects.create(
            nome='Milho colhido teste', categoria='SEMENTES', tipo_item='Milho em grão', unidade='kg'
        )
        racao = Produto.objects.create(
            nome='Ração produzida teste', categoria='SUPLEMENTOS', tipo_item='Ração bovina', unidade='saco'
        )
        Movimentacao.objects.create(
            produto=milho, tipo='ENTRADA', quantidade=Decimal('500.00'),
            origem_recurso='PRODUCAO_PROPRIA'
        )

        response = self.client.post(reverse('estoque:transferencia_nova'), {
            'produto_origem': milho.id,
            'quantidade_origem': '100',
            'produto_destino': racao.id,
            'quantidade_destino': '80',
            'origem_recurso': 'PRODUCAO_PROPRIA',
            'destino_tipo': 'PRODUCAO_PROPRIA',
            'data': date.today().isoformat(),
            'local_destino': 'Confinamento',
            'responsavel': 'Operador da fábrica',
            'observacoes': 'Conversão de milho em ração.',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(milho.saldo_atual, Decimal('400.00'))
        self.assertEqual(racao.saldo_atual, Decimal('80.00'))
        transferencia = TransferenciaRecurso.objects.get(produto_origem=milho, produto_destino=racao)
        self.assertEqual(transferencia.origem_recurso, 'PRODUCAO_PROPRIA')
        self.assertEqual(transferencia.movimentacao_entrada.origem_recurso, 'PRODUCAO_PROPRIA')

    def test_pendencia_persistente_nao_oculta_alerta_de_estoque(self):
        fungicida = Produto.objects.get(nome='Fungicida Tebuconazol 200 EC')
        painel_antes = self.client.get(reverse('estoque:painel'))
        self.assertTrue(any(
            alerta.get('produto_id') == fungicida.id and alerta.get('tipo') == 'ESTOQUE_CRITICO'
            for alerta in painel_antes.context['alertas']
        ))

        response_criacao = self.client.post(reverse('estoque:pendencia_nova'), {
            'titulo': 'Programar reposição do fungicida',
            'descricao': 'Solicitar três tambores ao fornecedor.',
            'prioridade': 'ALTA',
            'produto': fungicida.id,
            'ativo': '',
            'prazo': date.today().isoformat(),
        })
        self.assertEqual(response_criacao.status_code, 302)
        pendencia = PendenciaPrioritaria.objects.get(titulo='Programar reposição do fungicida')
        painel_com_tarefa = self.client.get(reverse('estoque:painel'))
        self.assertContains(painel_com_tarefa, 'Tarefa feita')

        response_conclusao = self.client.post(
            reverse('estoque:pendencia_status', args=[pendencia.id]),
            {'concluida': 'true'},
            follow=True,
        )
        self.assertEqual(response_conclusao.status_code, 200)
        self.assertContains(response_conclusao, 'continua ativo para')

        painel_depois = self.client.get(reverse('estoque:painel'))
        pendencia.refresh_from_db()
        self.assertTrue(pendencia.concluida)
        self.assertIsNotNone(pendencia.concluida_em)
        self.assertTrue(any(
            alerta.get('produto_id') == fungicida.id and alerta.get('tipo') == 'ESTOQUE_CRITICO'
            for alerta in painel_depois.context['alertas']
        ))
        self.assertFalse(any(
            item.pk == pendencia.pk for item in painel_depois.context['pendencias_abertas']
        ))
        self.assertTrue(any(
            item.pk == pendencia.pk for item in painel_depois.context['pendencias_concluidas']
        ))

    def test_tarefa_feita_confirma_alerta_resolvido_apos_reposicao(self):
        fungicida = Produto.objects.get(nome='Fungicida Tebuconazol 200 EC')
        pendencia = PendenciaPrioritaria.objects.create(
            titulo='Repor fungicida', prioridade='ALTA', produto=fungicida
        )
        Movimentacao.objects.create(
            produto=fungicida,
            tipo='ENTRADA',
            quantidade=Decimal('100.00'),
            data_movimentacao=date.today(),
            origem_recurso='COMPRA_EXTERNA',
        )

        response = self.client.post(
            reverse('estoque:pendencia_status', args=[pendencia.id]),
            {'concluida': 'true'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'não há alerta ativo para o item vinculado')
        self.assertFalse(any(
            alerta.get('produto_id') == fungicida.id and alerta.get('tipo') == 'ESTOQUE_CRITICO'
            for alerta in response.context['alertas']
        ))

    def test_status_de_manutencao_gera_alerta_prioritario_de_ativo(self):
        produto = Produto.objects.get(nome='Trator Massey Ferguson MF 4275 - TR-001')
        ativo, _ = AtivoRural.objects.get_or_create(produto=produto)
        ativo.status_manutencao = 'MANUTENCAO'
        ativo.save(update_fields=['status_manutencao'])

        response = self.client.get(reverse('estoque:painel'))

        alerta_ativo = next(
            alerta for alerta in response.context['alertas']
            if alerta.get('ativo_id') == ativo.id
        )
        self.assertEqual(alerta_ativo['prioridade'], 'ALTA')
        self.assertEqual(alerta_ativo['tipo'], 'MANUTENCAO_ATIVO')

    def test_ativo_duravel_nao_gera_alerta_falso_de_estoque_minimo(self):
        caminhonete = Produto.objects.get(nome='Caminhonete Toyota Hilux - Frota 01')

        alertas_produto = gerar_alertas_priorizados()

        self.assertFalse(any(
            alerta.get('produto_id') == caminhonete.id for alerta in alertas_produto
        ))

