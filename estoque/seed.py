"""
Módulo gerador de dados simulados fictícios para demonstração do AgroHack 2026/2.
Gera ~80 registros contemplando as 8 categorias do desafio e os casos de teste:
- 🔴 Estoque Crítico (saldo <= mínimo)
- 🔴 Lote Vencido com saldo
- 🔴 Risco de Perda por Validade Próxima
- 🟡 Estoque em Atenção (100% a 150% do mínimo)
- 🟡 Saída Anômala / Atípica (> 2 sigma)
- 🟢 Capital Imobilizado / Excesso
- ⚠️ Histórico Insuficiente (RN03)
- ⚠️ Valores ausentes não nulos (RN02)
"""

from datetime import date, timedelta
from decimal import Decimal
from .models import (
    AtivoRural,
    Lote,
    LoteAnimais,
    ManutencaoAtivo,
    Movimentacao,
    Produto,
    TransferenciaRecurso,
)


def popular_ativos_demonstracao():
    hoje = date.today()
    trator, _ = Produto.objects.get_or_create(
        nome="Trator Massey Ferguson MF 4275 - TR-001",
        defaults={
            'categoria': 'MAQUINAS',
            'tipo_item': 'Trator agrícola',
            'unidade': 'un',
            'tipo_embalagem': 'UNIDADE',
            'fabricante': 'Massey Ferguson',
            'modelo': 'MF 4275',
            'numero_serie': 'MF4275-AGRO-001',
            'ano_fabricacao': 2021,
            'estoque_minimo': Decimal('1.00'),
            'preco_referencia': Decimal('230000.00'),
            'descricao': 'Trator da frota para preparo de pasto e transporte de insumos.',
        },
    )
    if not trator.tipo_item:
        trator.tipo_item = 'Trator agrícola'
        trator.save(update_fields=['tipo_item'])
    trator_ativo, _ = AtivoRural.objects.get_or_create(
        produto=trator,
        defaults={
            'status_manutencao': 'OPERACIONAL',
            'consumo_medio': Decimal('12.00'),
            'unidade_consumo': 'L_H',
        },
    )
    Movimentacao.objects.get_or_create(
        produto=trator,
        tipo='ENTRADA',
        data_movimentacao=hoje - timedelta(days=180),
        defaults={
            'quantidade': Decimal('1.00'),
            'horimetro_h': Decimal('1280.5'),
            'preco_unitario': Decimal('230000.00'),
            'valor_total_pago': Decimal('230000.00'),
            'fornecedor': 'Concessionária Rural Jamari',
            'comprador': 'Setor de Patrimônio',
            'responsavel': 'Almoxarife da Fazenda',
        },
    )

    caminhonete, _ = Produto.objects.get_or_create(
        nome="Caminhonete Toyota Hilux - Frota 01",
        defaults={
            'categoria': 'VEICULOS',
            'tipo_item': 'Caminhonete 4x4',
            'unidade': 'un',
            'tipo_embalagem': 'UNIDADE',
            'fabricante': 'Toyota',
            'modelo': 'Hilux CD 4x4',
            'ano_fabricacao': 2022,
            'placa': 'ABC1D23',
            'chassi': '9BR00000000000001',
            'estoque_minimo': Decimal('1.00'),
            'preco_referencia': Decimal('190000.00'),
            'descricao': 'Veículo de apoio à pecuária e transporte entre retiros.',
        },
    )
    if not caminhonete.tipo_item:
        caminhonete.tipo_item = 'Caminhonete 4x4'
        caminhonete.save(update_fields=['tipo_item'])
    caminhonete_ativo, _ = AtivoRural.objects.get_or_create(
        produto=caminhonete,
        defaults={
            'status_manutencao': 'OPERACIONAL',
            'consumo_medio': Decimal('8.50'),
            'unidade_consumo': 'KM_L',
        },
    )
    Movimentacao.objects.get_or_create(
        produto=caminhonete,
        tipo='ENTRADA',
        data_movimentacao=hoje - timedelta(days=120),
        defaults={
            'quantidade': Decimal('1.00'),
            'odometro_km': Decimal('45210.5'),
            'preco_unitario': Decimal('190000.00'),
            'valor_total_pago': Decimal('190000.00'),
            'fornecedor': 'Concessionária Vale do Jamari',
            'comprador': 'Setor de Patrimônio',
            'responsavel': 'Almoxarife da Fazenda',
        },
    )
    ManutencaoAtivo.objects.get_or_create(
        ativo=trator_ativo,
        tipo='PREVENTIVA',
        data=hoje - timedelta(days=45),
        descricao='Revisão preventiva de demonstração',
        defaults={
            'horimetro_h': Decimal('1250.0'),
            'custo': Decimal('850.00'),
            'fornecedor': 'Oficina Rural Jamari',
            'responsavel': 'Mecânico da fazenda',
        },
    )

    ferramenta, _ = Produto.objects.get_or_create(
        nome='Motosserra STIHL MS 250 - FERR-001',
        defaults={
            'categoria': 'FERRAMENTAS',
            'tipo_item': 'Motosserra',
            'unidade': 'un',
            'fabricante': 'STIHL',
            'modelo': 'MS 250',
            'estoque_minimo': Decimal('1.00'),
            'preco_referencia': Decimal('2800.00'),
            'descricao': 'Ferramenta de manejo de cercas e limpeza de pasto.',
        },
    )
    if not ferramenta.tipo_item:
        ferramenta.tipo_item = 'Motosserra'
        ferramenta.save(update_fields=['tipo_item'])
    Movimentacao.objects.get_or_create(
        produto=ferramenta,
        tipo='ENTRADA',
        data_movimentacao=hoje - timedelta(days=90),
        defaults={
            'quantidade': Decimal('2.00'),
            'preco_unitario': Decimal('2800.00'),
            'valor_total_pago': Decimal('5600.00'),
            'fornecedor': 'Ferramentas Vale do Jamari',
            'comprador': 'Setor de Patrimônio',
            'responsavel': 'Almoxarife da Fazenda',
        },
    )

    oleo, _ = Produto.objects.get_or_create(
        nome='Óleo lubrificante de motor 15W40 - tambor',
        defaults={
            'categoria': 'COMBUSTIVEIS',
            'tipo_item': 'Óleo de motor 15W40',
            'unidade': 'L',
            'tipo_embalagem': 'TAMBOR',
            'volume_embalagem_ml': Decimal('200000.00'),
            'estoque_minimo': Decimal('100.00'),
            'preco_referencia': Decimal('18.00'),
            'descricao': 'Óleo lubrificante para motores da frota agrícola.',
        },
    )
    if not oleo.tipo_item:
        oleo.tipo_item = 'Óleo de motor 15W40'
        oleo.save(update_fields=['tipo_item'])
    Movimentacao.objects.get_or_create(
        produto=oleo,
        tipo='ENTRADA',
        data_movimentacao=hoje - timedelta(days=30),
        defaults={
            'quantidade': Decimal('200.00'),
            'preco_unitario': Decimal('18.00'),
            'valor_total_pago': Decimal('3600.00'),
            'fornecedor': 'Lubrificantes Rondônia',
            'comprador': 'Setor de Compras',
            'responsavel': 'Almoxarife da Fazenda',
        },
    )
    Movimentacao.objects.get_or_create(
        produto=oleo,
        tipo='SAIDA',
        data_movimentacao=hoje - timedelta(days=20),
        ativo=trator_ativo,
        defaults={
            'quantidade': Decimal('12.00'),
            'destino': trator.nome,
            'responsavel': 'Mecânico da fazenda',
            'origem_recurso': 'COMPRA_EXTERNA',
        },
    )

    diesel = Produto.objects.filter(nome='Óleo Diesel S10 Granel').first()
    if diesel:
        Movimentacao.objects.get_or_create(
            produto=diesel,
            tipo='SAIDA',
            data_movimentacao=hoje - timedelta(days=5),
            ativo=caminhonete_ativo,
            defaults={
                'quantidade': Decimal('60.00'),
                'destino': caminhonete.nome,
                'responsavel': 'Operador da frota',
                'origem_recurso': 'COMPRA_EXTERNA',
                'odometro_km': Decimal('45600.0'),
            },
        )

    milho, _ = Produto.objects.get_or_create(
        nome='Milho em grão - Produção própria',
        defaults={
            'categoria': 'INSUMOS',
            'tipo_item': 'Milho em grão',
            'unidade': 'kg',
            'estoque_minimo': Decimal('100.00'),
            'descricao': 'Grão colhido na propriedade para uso interno e formulação de ração.',
        },
    )
    milho_entrada, _ = Movimentacao.objects.get_or_create(
        produto=milho,
        tipo='ENTRADA',
        data_movimentacao=hoje - timedelta(days=60),
        defaults={
            'quantidade': Decimal('500.00'),
            'origem_recurso': 'PRODUCAO_PROPRIA',
            'destino': 'Silo da fazenda',
            'responsavel': 'Equipe agrícola',
        },
    )
    racao, _ = Produto.objects.get_or_create(
        nome='Ração bovina - Produção interna',
        defaults={
            'categoria': 'SUPLEMENTOS',
            'tipo_item': 'Ração bovina',
            'unidade': 'saco',
            'tipo_embalagem': 'SACO',
            'peso_embalagem_kg': Decimal('25.000'),
            'estoque_minimo': Decimal('20.00'),
            'descricao': 'Ração produzida internamente a partir de grãos da propriedade.',
        },
    )
    milho_saida, _ = Movimentacao.objects.get_or_create(
        produto=milho,
        tipo='SAIDA',
        data_movimentacao=hoje - timedelta(days=40),
        defaults={
            'quantidade': Decimal('350.00'),
            'origem_recurso': 'PRODUCAO_PROPRIA',
            'destino': racao.nome,
            'responsavel': 'Equipe da fábrica de ração',
        },
    )
    racao_entrada, _ = Movimentacao.objects.get_or_create(
        produto=racao,
        tipo='ENTRADA',
        data_movimentacao=hoje - timedelta(days=40),
        defaults={
            'quantidade': Decimal('14.00'),
            'origem_recurso': 'PRODUCAO_PROPRIA',
            'destino': 'Confinamento',
            'responsavel': 'Equipe da fábrica de ração',
        },
    )
    TransferenciaRecurso.objects.get_or_create(
        produto_origem=milho,
        produto_destino=racao,
        data=hoje - timedelta(days=40),
        defaults={
            'quantidade_origem': Decimal('350.00'),
            'quantidade_destino': Decimal('14.00'),
            'origem_recurso': 'PRODUCAO_PROPRIA',
            'destino_tipo': 'PRODUCAO_PROPRIA',
            'local_destino': 'Confinamento',
            'responsavel': 'Equipe da fábrica de ração',
            'observacoes': '350 kg de milho convertidos em 14 sacos de ração de 25 kg.',
            'movimentacao_saida': milho_saida,
            'movimentacao_entrada': racao_entrada,
        },
    )

    tipos_de_demo = {
        'Fungicida Tebuconazol 200 EC': 'Fungicida',
        'Vacina Antiaftosa Bivalente 50 Doses': 'Vacina antiaftosa',
        'Oxitetraciclina L.A. 200mg/ml 50ml': 'Antibiótico injetável',
        'Óleo Diesel S10 Granel': 'Diesel S10',
        'Ureia Agrícola 46% N': 'Fertilizante nitrogenado',
        'Semente Brachiaria brizantha cv. Marandu': 'Semente de pastagem',
        'Filtro de Óleo Lubrificante Trator Valtra BH180': 'Filtro de óleo',
        'Sal Mineral Bovino 80 Fos 30kg': 'Suplemento mineral',
        'Respirador Facial com Filtro de Carvão Ativado 3M': 'Respirador facial',
        'Herbicida Glifosato 480 SL': 'Herbicida',
    }
    for nome, tipo_item in tipos_de_demo.items():
        Produto.objects.filter(nome=nome, tipo_item='').update(tipo_item=tipo_item)


def popular_dados_demonstracao():
    # Limpa dados existentes para garantir idempotência na demonstração
    TransferenciaRecurso.objects.all().delete()
    ManutencaoAtivo.objects.all().delete()
    AtivoRural.objects.all().delete()
    Movimentacao.objects.all().delete()
    Lote.objects.all().delete()
    LoteAnimais.objects.all().delete()
    Produto.objects.all().delete()

    hoje = date.today()

    # =========================================================================
    # 1. DEFENSIVOS: Fungicida Tebuconazol (🔴 ESTOQUE CRÍTICO)
    # =========================================================================
    p_fungicida = Produto.objects.create(
        nome="Fungicida Tebuconazol 200 EC",
        categoria="DEFENSIVOS",
        tipo_item="Fungicida",
        unidade="L",
        estoque_minimo=Decimal("50.00"),
        preco_referencia=Decimal("95.00"),
        descricao="Fungicida sistêmico para controle de ferrugem e manchas foliares."
    )
    lote_fung = Lote.objects.create(
        produto=p_fungicida,
        numero_lote="LT-TBZ-2025-01",
        data_validade=hoje + timedelta(days=180)
    )
    # Entrada inicial de 100 L há 90 dias
    Movimentacao.objects.create(
        produto=p_fungicida, lote=lote_fung, tipo="ENTRADA", quantidade=Decimal("100.00"),
        data_movimentacao=hoje - timedelta(days=90), preco_unitario=Decimal("95.00"),
        fornecedor="Agro Química Rondônia", destino="Depósito Central", responsavel="João Silva"
    )
    # Saídas sucessivas que rebaixam o saldo para 18 L (abaixo do mínimo de 50 L)
    for i, dias in enumerate([60, 45, 30, 15, 5]):
        Movimentacao.objects.create(
            produto=p_fungicida, lote=lote_fung, tipo="SAIDA", quantidade=Decimal("16.40"),
            data_movimentacao=hoje - timedelta(days=dias),
            destino="Talhão 02 - Soja", responsavel="Carlos Tratorista"
        )
    # Saldo resultante = 100 - (5 * 16.40) = 18 L (CRÍTICO!)

    # =========================================================================
    # 2. MEDICAMENTOS: Vacina Antiaftosa (🔴 RISCO DE PERDA POR VALIDADE)
    # =========================================================================
    p_vacina = Produto.objects.create(
        nome="Vacina Antiaftosa Bivalente 50 Doses",
        categoria="MEDICAMENTOS",
        tipo_item="Vacina antiaftosa",
        unidade="dose",
        estoque_minimo=Decimal("100.00"),
        preco_referencia=Decimal("2.80"),
        descricao="Vacina obrigatória para imunização do rebanho bovino."
    )
    lote_vac = Lote.objects.create(
        produto=p_vacina,
        numero_lote="LT-AFT-26B",
        data_validade=hoje + timedelta(days=12)  # Vence em 12 dias!
    )
    Movimentacao.objects.create(
        produto=p_vacina, lote=lote_vac, tipo="ENTRADA", quantidade=Decimal("300.00"),
        data_movimentacao=hoje - timedelta(days=40), preco_unitario=Decimal("2.80"),
        fornecedor="Distribuidora Veterinária Jamari", destino="Geladeira Veterinária", responsavel="Dra. Bruna"
    )
    # Saída pequena de 50 doses há 10 dias. Restam 250 doses para vencer em 12 dias (Risco de Perda!)
    Movimentacao.objects.create(
        produto=p_vacina, lote=lote_vac, tipo="SAIDA", quantidade=Decimal("50.00"),
        data_movimentacao=hoje - timedelta(days=10),
        destino="Lote Bezerros Desmama", responsavel="Marcos Vaqueiro"
    )
    Movimentacao.objects.create(
        produto=p_vacina, lote=lote_vac, tipo="SAIDA", quantidade=Decimal("30.00"),
        data_movimentacao=hoje - timedelta(days=3),
        destino="Lote Novilhas", responsavel="Marcos Vaqueiro"
    )

    # =========================================================================
    # 3. MEDICAMENTOS: Oxitetraciclina L.A. (🔴 LOTE VENCIDO COM SALDO)
    # =========================================================================
    p_oxitetra = Produto.objects.create(
        nome="Oxitetraciclina L.A. 200mg/ml 50ml",
        categoria="MEDICAMENTOS",
        tipo_item="Antibiótico injetável",
        unidade="frasco",
        estoque_minimo=Decimal("5.00"),
        preco_referencia=Decimal("42.00"),
        descricao="Antibiótico injetável de longa ação para infecções bacterianas."
    )
    lote_oxi_venc = Lote.objects.create(
        produto=p_oxitetra,
        numero_lote="LT-OXI-2024",
        data_validade=hoje - timedelta(days=8)  # Vencido há 8 dias!
    )
    Movimentacao.objects.create(
        produto=p_oxitetra, lote=lote_oxi_venc, tipo="ENTRADA", quantidade=Decimal("10.00"),
        data_movimentacao=hoje - timedelta(days=200), preco_unitario=Decimal("40.00"),
        fornecedor="Agropecuária Ariquemes", destino="Farmácia Veterinária", responsavel="Dra. Bruna"
    )
    Movimentacao.objects.create(
        produto=p_oxitetra, lote=lote_oxi_venc, tipo="SAIDA", quantidade=Decimal("6.00"),
        data_movimentacao=hoje - timedelta(days=60),
        destino="Enfermaria Bovinos", responsavel="Dra. Bruna"
    )
    # Sobram 4 frascos vencidos!

    # =========================================================================
    # 4. COMBUSTÍVEIS: Óleo Diesel S10 (🟡 SAÍDA ANÔMALA / > 2 SIGMA)
    # =========================================================================
    p_diesel = Produto.objects.create(
        nome="Óleo Diesel S10 Granel",
        categoria="COMBUSTIVEIS",
        tipo_item="Diesel S10",
        unidade="L",
        estoque_minimo=Decimal("1000.00"),
        preco_referencia=Decimal("6.15"),
        descricao="Abastecimento da frota de tratores e colheitadeiras."
    )
    lote_diesel = Lote.objects.create(
        produto=p_diesel,
        numero_lote="LT-DSL-2026",
        data_validade=hoje + timedelta(days=365)
    )
    Movimentacao.objects.create(
        produto=p_diesel, lote=lote_diesel, tipo="ENTRADA", quantidade=Decimal("8000.00"),
        data_movimentacao=hoje - timedelta(days=120), preco_unitario=Decimal("6.10"),
        fornecedor="Posto & TRR Rondônia", destino="Tanque Principal", responsavel="José Almoxarife"
    )
    # 7 saídas normais de ~200 a 250 L
    for dias, qtd in [(100, 210), (85, 230), (70, 190), (55, 220), (40, 240), (25, 205), (12, 215)]:
        Movimentacao.objects.create(
            produto=p_diesel, lote=lote_diesel, tipo="SAIDA", quantidade=Decimal(str(qtd)),
            data_movimentacao=hoje - timedelta(days=dias),
            destino="Trator John Deere 6110", responsavel="Sebastião Operador"
        )
    # 1 saída brutalmente atípica de 1800 L (Anomalia > 2 sigma!)
    Movimentacao.objects.create(
        produto=p_diesel, lote=lote_diesel, tipo="SAIDA", quantidade=Decimal("1800.00"),
        data_movimentacao=hoje - timedelta(days=2),
        destino="Operação Especial Gradagem Pesada", responsavel="Sebastião Operador"
    )

    # =========================================================================
    # 5. FERTILIZANTES: Ureia Agrícola 46% (🟡 ESTOQUE EM ATENÇÃO)
    # =========================================================================
    p_ureia = Produto.objects.create(
        nome="Ureia Agrícola 46% N",
        categoria="FERTILIZANTES",
        tipo_item="Fertilizante nitrogenado",
        unidade="sc",
        estoque_minimo=Decimal("40.00"),
        preco_referencia=Decimal("145.00"),
        descricao="Adubação nitrogenada de cobertura para pastagens e milho."
    )
    lote_ureia = Lote.objects.create(
        produto=p_ureia,
        numero_lote="LT-URE-99A",
        data_validade=hoje + timedelta(days=300)
    )
    Movimentacao.objects.create(
        produto=p_ureia, lote=lote_ureia, tipo="ENTRADA", quantidade=Decimal("120.00"),
        data_movimentacao=hoje - timedelta(days=75), preco_unitario=Decimal("140.00"),
        fornecedor="Fertilizantes Guaporé", destino="Barracão de Insumos", responsavel="João Silva"
    )
    # Saídas que deixam o saldo em 50 sacos (entre 40 e 60, ou seja, <= 1.5x mínimo) -> ATENÇÃO
    for dias in [60, 45, 30, 15]:
        Movimentacao.objects.create(
            produto=p_ureia, lote=lote_ureia, tipo="SAIDA", quantidade=Decimal("17.50"),
            data_movimentacao=hoje - timedelta(days=dias),
            destino="Piquetes Rotacionados 01 a 04", responsavel="Carlos Tratorista"
        )

    # =========================================================================
    # 6. SEMENTES: Brachiaria brizantha (🟢 EXCESSO / CAPITAL PARADO)
    # =========================================================================
    p_semente = Produto.objects.create(
        nome="Semente Brachiaria brizantha cv. Marandu",
        categoria="SEMENTES",
        tipo_item="Semente de pastagem",
        unidade="kg",
        estoque_minimo=Decimal("200.00"),
        preco_referencia=Decimal("28.00"),
        descricao="Semente com 80% de valor cultural para reforma de pastagens."
    )
    lote_sem = Lote.objects.create(
        produto=p_semente,
        numero_lote="LT-BRZ-2026",
        data_validade=hoje + timedelta(days=240)
    )
    Movimentacao.objects.create(
        produto=p_semente, lote=lote_sem, tipo="ENTRADA", quantidade=Decimal("1200.00"),
        data_movimentacao=hoje - timedelta(days=90), preco_unitario=Decimal("28.00"),
        fornecedor="Sementes Campo Belo", destino="Depósito Climatizado", responsavel="João Silva"
    )
    # Apenas 50 kg saíram. Saldo = 1150 kg (valor total R$ 32.200, 5x acima do mínimo de 200 kg)
    Movimentacao.objects.create(
        produto=p_semente, lote=lote_sem, tipo="SAIDA", quantidade=Decimal("50.00"),
        data_movimentacao=hoje - timedelta(days=40),
        destino="Reforma Piquete Maternidade", responsavel="Marcos Vaqueiro"
    )

    # =========================================================================
    # 7. MANUTENÇÃO: Filtro de Óleo Trator Valtra (🔴 ESTOQUE CRÍTICO)
    # =========================================================================
    p_filtro = Produto.objects.create(
        nome="Filtro de Óleo Lubrificante Trator Valtra BH180",
        categoria="MANUTENCAO",
        tipo_item="Filtro de óleo",
        unidade="un",
        estoque_minimo=Decimal("3.00"),
        preco_referencia=Decimal("85.00"),
        descricao="Elemento filtrante para manutenção periódica de 250 horas."
    )
    Movimentacao.objects.create(
        produto=p_filtro, tipo="ENTRADA", quantidade=Decimal("4.00"),
        data_movimentacao=hoje - timedelta(days=120), preco_unitario=Decimal("82.00"),
        fornecedor="Trator Peças Rondônia", destino="Oficina Mecânica", responsavel="Mecânico Antenor"
    )
    # 3 saídas ao longo das revisões -> Saldo = 1 un (crítico!)
    for dias in [90, 50, 10]:
        Movimentacao.objects.create(
            produto=p_filtro, tipo="SAIDA", quantidade=Decimal("1.00"),
            data_movimentacao=hoje - timedelta(days=dias),
            destino="Revisão Periódica BH180", responsavel="Mecânico Antenor"
        )

    # =========================================================================
    # 8. SUPLEMENTOS: Sal Mineral Bovino 80 Fos (REGULAR / SEGURO)
    # =========================================================================
    p_sal = Produto.objects.create(
        nome="Sal Mineral Bovino 80 Fos 30kg",
        categoria="SUPLEMENTOS",
        tipo_item="Suplemento mineral",
        unidade="sc",
        estoque_minimo=Decimal("30.00"),
        preco_referencia=Decimal("88.00"),
        descricao="Suplemento mineral completo para gado de corte nas águas."
    )
    lote_sal = Lote.objects.create(
        produto=p_sal,
        numero_lote="LT-SAL-2026-FOS",
        data_validade=hoje + timedelta(days=400)
    )
    Movimentacao.objects.create(
        produto=p_sal, lote=lote_sal, tipo="ENTRADA", quantidade=Decimal("150.00"),
        data_movimentacao=hoje - timedelta(days=110), preco_unitario=Decimal("85.00"),
        fornecedor="Nutrição Animal Nutrir", destino="Barracão do Sal", responsavel="João Silva"
    )
    # Saídas regulares a cada 15 dias de 10 sacos -> Saldo atual = 80 sacos (seguro!)
    for dias in [100, 85, 70, 55, 40, 25, 10]:
        Movimentacao.objects.create(
            produto=p_sal, lote=lote_sal, tipo="SAIDA", quantidade=Decimal("10.00"),
            data_movimentacao=hoje - timedelta(days=dias),
            destino="Cocheiras Retiro 01 e 02", responsavel="Marcos Vaqueiro"
        )

    # =========================================================================
    # 9. EPI: Máscara com Filtro Carvão Ativado (⚠️ HISTÓRICO INSUFICIENTE - RN03)
    # =========================================================================
    p_epi = Produto.objects.create(
        nome="Respirador Facial com Filtro de Carvão Ativado 3M",
        categoria="EPI",
        tipo_item="Respirador facial",
        unidade="un",
        estoque_minimo=Decimal("5.00"),
        preco_referencia=Decimal("65.00"),
        descricao="Proteção respiratória para aplicação de defensivos agrícolas."
    )
    # Apenas 1 entrada recente, sem saídas -> teste do RN03 (não deve inventar consumo zero nem previsão)
    Movimentacao.objects.create(
        produto=p_epi, tipo="ENTRADA", quantidade=Decimal("12.00"),
        data_movimentacao=hoje - timedelta(days=15), preco_unitario=Decimal("65.00"),
        fornecedor="Segurança do Trabalho Ariquemes", destino="Almoxarifado EPI", responsavel="João Silva"
    )

    # =========================================================================
    # 10. DEFENSIVOS: Herbicida Glifosato 480 SL (CURVA TEMPORAL RICA - RF03.6)
    # =========================================================================
    p_glifosato = Produto.objects.create(
        nome="Herbicida Glifosato 480 SL",
        categoria="DEFENSIVOS",
        tipo_item="Herbicida",
        unidade="L",
        estoque_minimo=Decimal("100.00"),
        preco_referencia=Decimal("38.00"),
        descricao="Herbicida sistêmico não seletivo para dessecação pré-plantio."
    )
    lote_glif = Lote.objects.create(
        produto=p_glifosato,
        numero_lote="LT-GLI-2025-C",
        data_validade=hoje + timedelta(days=210)
    )
    Movimentacao.objects.create(
        produto=p_glifosato, lote=lote_glif, tipo="ENTRADA", quantidade=Decimal("1500.00"),
        data_movimentacao=hoje - timedelta(days=160), preco_unitario=Decimal("36.50"),
        fornecedor="Agro Química Rondônia", destino="Depósito Químicos", responsavel="João Silva"
    )
    # Saídas distribuídas nos últimos 5 meses mostrando sazonalidade de preparo de solo
    historico_glifosato = [
        (150, 200), (130, 250), (100, 350), (70, 150), (40, 120), (15, 80)
    ]
    for dias, qtd in historico_glifosato:
        Movimentacao.objects.create(
            produto=p_glifosato, lote=lote_glif, tipo="SAIDA", quantidade=Decimal(str(qtd)),
            data_movimentacao=hoje - timedelta(days=dias),
            destino="Dessecação Talhões 01 a 05", responsavel="Carlos Tratorista"
        )

    # =========================================================================
    # LOTES DE ANIMAIS (Manejo Bovino - Corte, Leite, Recria, Cria)
    # =========================================================================
    LoteAnimais.objects.create(
        nome="Lote 01 - Garrotes Nelore",
        categoria="CORTE",
        quantidade_cabecas=150,
        pasto_localizacao="Pasto Piquete 04 (Brachiaria)",
        escore_corporal=Decimal("3.2"),
        peso_medio_estimado=Decimal("380.00"),
        consumo_diario_cabeca=Decimal("0.120"),
        insumo_suplementar=p_sal,
        observacoes="Garrotes em fase de recria e engorda a pasto com suplementação mineral diária."
    )

    LoteAnimais.objects.create(
        nome="Lote 02 - Vacas em Lactação Girolando",
        categoria="LEITE",
        quantidade_cabecas=85,
        pasto_localizacao="Piquete Rotacionado 01 (Mombaça)",
        escore_corporal=Decimal("3.8"),
        peso_medio_estimado=Decimal("520.00"),
        consumo_diario_cabeca=Decimal("0.150"),
        insumo_suplementar=p_sal,
        observacoes="Plantel leiteiro de alta produção (Bacia Leiteira Ariquemes/RO). Suplementação mineral + volumoso."
    )

    LoteAnimais.objects.create(
        nome="Lote 03 - Novilhas Sobreamano",
        categoria="RECRIA",
        quantidade_cabecas=120,
        pasto_localizacao="Pasto Piquete 07 (Marandu)",
        escore_corporal=Decimal("3.0"),
        peso_medio_estimado=Decimal("310.00"),
        consumo_diario_cabeca=Decimal("0.100"),
        insumo_suplementar=p_sal,
        observacoes="Lote de reposição de matrizes para a próxima estação de monta."
    )

    LoteAnimais.objects.create(
        nome="Lote 04 - Bezerros Desmama",
        categoria="CRIA",
        quantidade_cabecas=105,
        pasto_localizacao="Piquete Maternidade e Retiro",
        escore_corporal=Decimal("2.8"),
        peso_medio_estimado=Decimal("190.00"),
        consumo_diario_cabeca=Decimal("0.080"),
        insumo_suplementar=p_sal,
        observacoes="Bezerros recém-desmamados. Requer atenção ao ECC e imunização preventiva."
    )

    popular_ativos_demonstracao()

    total_movs = Movimentacao.objects.count()
    return total_movs


if __name__ == "__main__":
    import django
    django.setup()
    popular_dados_demonstracao()
