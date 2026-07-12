import csv

from django.core.management.base import BaseCommand

from api.models import Ingredient, Unit


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
                unit, _ = Unit.objects.get_or_create(
                    symbol=row[1]
                )

                ingredients.append(
                    Ingredient(
                        name=row[0],
                        measurement_unit=unit
                    )
                )

            Ingredient.objects.bulk_create(
                ingredients
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Ингредиенты загружены'
            )
        )
