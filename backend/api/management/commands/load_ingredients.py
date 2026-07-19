import csv

from django.core.management.base import BaseCommand

from api.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов'

    def handle(self, *args, **options):

        with open(
            'data/ingredients.csv',
            encoding='utf-8'
        ) as file:
            reader = csv.reader(file)

            ingredients = []

            for row in reader:
                ingredients.append(
                    Ingredient(
                        name=row[0],
                        measurement_unit=row[1]
                    )
                )

            Ingredient.objects.bulk_create(
                ingredients,
                ignore_conflicts=True
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Ингредиенты загружены'
            )
        )
