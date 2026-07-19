from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (Ingredient,
                     Recipe, Subscription,
                     Tag, RecipeIngredient, User as CustomUser)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
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
    list_display = (
        'name',
        'author',
        'image',
        'cooking_time',
    )
    list_display = ('name', 'author', 'cooking_time',)
    search_fields = ('author__username', 'name',)
    list_filter = ('author', 'tags',)
    inlines = (RecipeIngredientInline,)

    @admin.display(description='В избранном')
    def favorites_count(self, obj):
        return obj.favorited_by.count()
