import django_filters
from api.models import Recipe, Tag
from rest_framework.filters import SearchFilter


class CharFilterIn(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False,
    )

    author = django_filters.NumberFilter(
        field_name='author_id'
    )

    is_favorited = django_filters.CharFilter(
        method='filter_favorite'
    )

    is_in_shopping_cart = django_filters.CharFilter(
        method='filter_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def filter_favorite(self, queryset, name, value):
        if value == '1' and self.request.user.is_authenticated:
            return queryset.filter(
                favorited_by=self.request.user
            )
        return queryset

    def filter_shopping_cart(self, queryset, name, value):
        if value == '1' and self.request.user.is_authenticated:
            return queryset.filter(
                shopping_list=self.request.user
            )
        return queryset


class IngredientsSearchFilter(SearchFilter):
    search_param = 'name'
