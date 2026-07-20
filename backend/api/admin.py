from django.contrib import admin
from django.db.models import Count
from django.contrib.auth.admin import UserAdmin

from .models import (Ingredient,
                     Recipe, Subscription, Favorite, ShoppingCart,
                     Tag, RecipeIngredient, User as BaseUser)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1


@admin.register(BaseUser)
class UserAdmin(UserAdmin):
    list_display = ('username', 'email',)
    search_fields = ('username', 'email',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'author',
    )
    search_fields = (
        'user__username',
        'author__username',
    )
    list_filter = (
        'user',
        'author',
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
        'created',
    )
    ordering = ('-created',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
        'created',
    )
    ordering = ('-created',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'measurement_unit',)
    list_filter = ('measurement_unit',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'cooking_time', 'favorites_count')
    search_fields = ('author__username', 'name',)
    list_filter = ('author', 'tags',)
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.annotate(
            _favorites_count=Count('favorite', distinct=True)
        )

    @admin.display(description='В избранном')
    def favorites_count(self, obj):

        return getattr(obj, '_favorites_count', 0)
