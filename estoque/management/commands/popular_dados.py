from django.core.management.base import BaseCommand
from estoque.seed import popular_dados_demonstracao


class Command(BaseCommand):
    help = 'Popula a base do SQLite com dados fictícios de demonstração para o AgroHack 2026/2'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Iniciando carga de dados fictícios de demonstração...'))
        total = popular_dados_demonstracao()
        self.stdout.write(self.style.SUCCESS(
            f'Sucesso! Base populada com {total} movimentações fictícias cobrindo as 8 categorias do desafio e cenários de teste.'
        ))
