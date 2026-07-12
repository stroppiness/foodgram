from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (GetIngredientsViewSet, GetOrRemoveTokenViewSet,
                    GetRecipesViewSet, GetSubstriptionViewset, GetTagViewSet,
                    GetUserViewSet, SignUpView)

router = DefaultRouter()
router.register(
    'users/subscriptions',
    GetSubstriptionViewset,
    basename='subscriptions'
)
router.register('auth/token', GetOrRemoveTokenViewSet, basename='auth-token')
router.register('users', GetUserViewSet, basename='users')
router.register('tags', GetTagViewSet)
router.register('recipes', GetRecipesViewSet)
router.register('ingredients', GetIngredientsViewSet)
urlpatterns = [
    path('', include(router.urls)),
    path('users/', SignUpView.as_view()),
]
