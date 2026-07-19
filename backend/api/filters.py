import django_filters
from rest_framework.filters import SearchFilter
from django_filters.widgets import BooleanWidget

from .models import Recipe, Tag


class RecipeFilter(django_filters.FilterSet):

    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )

    is_favorited = django_filters.BooleanFilter(widget=BooleanWidget())
    is_in_shopping_cart = django_filters.BooleanFilter(widget=BooleanWidget())

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'is_favorited',
        )


class IngredientsSearchFilter(SearchFilter):
    search_param = 'name'
