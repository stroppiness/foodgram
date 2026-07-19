from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (GetIngredientsViewSet,
                    GetRecipesViewSet, GetSubscriptionViewset, GetTagViewSet,
                    GetUserViewSet, short_recipe_link)

router = DefaultRouter()
router.register(
    'users/subscriptions',
    GetSubscriptionViewset,
    basename='subscriptions'
)
router.register('users', GetUserViewSet, basename='users')
router.register('tags', GetTagViewSet, basename='tags')
router.register('recipes', GetRecipesViewSet, basename='recipes')
router.register('ingredients', GetIngredientsViewSet, basename='ingredients')
urlpatterns = [
    path('', include(router.urls)),
    path('s/<int:recipe_id>/', short_recipe_link, name='short-recipe'),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken'))
]
