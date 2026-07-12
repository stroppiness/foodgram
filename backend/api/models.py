from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Subscription(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='subscriptions'
                             )
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='subscribers'
                               )

    def __str__(self):
        return f"Subscription: {self.user} -> {self.author}"

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F('author')),
                name='no_self_subscription'
            )
        ]


class Tag(models.Model):
    name = models.CharField(max_length=50,
                            unique=True,
                            verbose_name='Название'
                            )
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'


class Unit(models.Model):
    name = models.CharField(max_length=50, verbose_name='Cимвол')
    symbol = models.CharField(max_length=10, verbose_name='Название')

    def __str__(self):
        return self.symbol

    class Meta:
        verbose_name = 'Единица измерения'
        verbose_name_plural = 'Единицы измерения'


class Ingredient(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    measurement_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT, verbose_name='Единица измерения',
        related_name='measurement_unit',
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='recipes/')
    text = models.TextField()
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        related_name='recipes'
    )
    cooking_time = models.PositiveIntegerField()
    shopping_list = models.ManyToManyField(User, related_name='shopping_list')
    favorited_by = models.ManyToManyField(User,
                                          related_name='favorite_recipes')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe,
                               on_delete=models.CASCADE,
                               related_name='recipe_ingredients'
                               )
    ingredient = models.ForeignKey(Ingredient,
                                   on_delete=models.CASCADE,
                                   related_name='recipe_ingredients'
                                   )
    amount = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.recipe} - {self.ingredient} ({self.amount})'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            )
        ]
