from django.db.models import Exists, OuterRef, Sum, Count, Value, BooleanField
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .create_shopping_txt import create_shopping_list
from .filters import IngredientsSearchFilter, RecipeFilter
from .models import (Ingredient, Recipe, Subscription,
                     Tag, User, ShoppingCart, Favorite, RecipeIngredient,
                     Subscription)
from .pagination import Pagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (ChangePasswordSerializer, GetTagSerializer,
                          GetUserSerializer,
                          IngredientSerializer,
                          PostSubscriptionSerializer, PutAvatarSerializer,
                          RecipesGetSerializer, RecipesPostSerializer,
                          ShoppingCartSerializer, SignupSerializer)


class GetUserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = User.objects.all()
    pagination_class = Pagination
    """
    Общий вьюсет для ресурса users.
    """

    def get_permissions(self):
        if self.action in ('me', 'avatar', 'set_password'):
            return [IsAuthenticated()]
        elif self.action in ('create', 'list', 'retrieve'):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'avatar':
            return PutAvatarSerializer
        elif self.action == 'set_password':
            return ChangePasswordSerializer
        return GetUserSerializer

    def get_queryset(self):
        queryset = User.objects.all()

        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_subscribed=Exists(
                    Subscription.objects.filter(
                        user=self.request.user,
                        author=OuterRef('pk')
                    )
                )
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            SignupSerializer(user, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=['get'],
        url_path='me'
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar'
    )
    def avatar(self, request):

        if request.method == 'PUT':
            serializer = self.get_serializer(request.user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(serializer.data)

        elif request.method == 'DELETE':
            request.user.avatar.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data,
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        url_path='subscribe',
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()

        if request.user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            author=author
        )

        if not created:
            return Response(
                {'errors': 'Подписка уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PostSubscriptionSerializer(
            author,
            context={'request': request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def delete_subscribe(self, request, pk=None):
        author = self.get_object()

        deleted, _ = Subscription.objects.filter(
            user=request.user,
            author=author
        ).delete()

        if not deleted:
            return Response(
                {'errors': 'Вы не подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class GetSubscriptionViewset(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для get-запроса ресурса subscription.
    """
    serializer_class = PostSubscriptionSerializer
    pagination_class = Pagination

    def get_queryset(self):
        queryset = User.objects.all()

        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_subscribed=Exists(
                    Subscription.objects.filter(
                        user=self.request.user,
                        author=OuterRef('pk')
                    )
                ),
                recipes_count=Count('recipes')
            )

        return queryset


class GetTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для ресурса Tags.
    """
    queryset = Tag.objects.all()
    serializer_class = GetTagSerializer
    permission_classes = [AllowAny]


def short_recipe_link(request, recipe_id):
    """
    Перенаправляет принятый запрос на фронт.
    """
    get_object_or_404(Recipe, id=recipe_id)

    return redirect(f'/recipes/{recipe_id}/')


class GetRecipesViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для ресурса Recipes.
    """
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = Pagination
    filterset_class = RecipeFilter
    filter_backends = (
        DjangoFilterBackend,
        SearchFilter,
    )
    search_fields = (
        'name',
        'author__username',
    )

    def get_permissions(self):
        if self.action in (
            'add_shopping_cart',
            'remove_shopping_cart',
            'add_remove_favorite',
        ):
            return [permissions.IsAuthenticated()]

        return [IsAuthorOrReadOnly()]

    def get_serializer_class(self):

        if self.action in ('create', 'update', 'partial_update'):
            return RecipesPostSerializer

        if self.action in ('add_shopping_cart', 'add_remove_favorite'):
            return ShoppingCartSerializer

        return RecipesGetSerializer

    def get_queryset(self):
        queryset = (
            Recipe.objects
            .select_related('author')
            .prefetch_related(
                'tags',
                'recipe_ingredients__ingredient'
            )
        )

        user = self.request.user

        if user.is_authenticated:
            queryset = queryset.annotate(
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                ),
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                )
            )
        else:
            queryset = queryset.annotate(
                is_in_shopping_cart=Value(
                    False,
                    output_field=BooleanField()
                ),
                is_favorited=Value(
                    False,
                    output_field=BooleanField()
                )
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()

        url = reverse('short-recipe', kwargs={'recipe_id': recipe.id})

        short_url = request.build_absolute_uri(url)

        return Response({
            'short-link': short_url,
        }, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
    )
    def get_shopping_cart_txt(self, request):
        ingredients = (RecipeIngredient.objects.filter(
            recipe__shoppingcart__user=request.user)
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        )

        text = create_shopping_list(ingredients)

        response = HttpResponse(text, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )

        return response

    @action(
        detail=True,
        methods=['post'],
        url_path='shopping_cart',
    )
    def add_shopping_cart(self, request, pk=None):
        recipe = self.get_object()

        if ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен в корзину'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ShoppingCart.objects.create(
            user=request.user,
            recipe=recipe
        )

        serializer = self.get_serializer(recipe)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @add_shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        recipe = self.get_object()

        deleted, _ = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()

        if not deleted:
            return Response(
                {'errors': 'Рецепта нет в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
    )
    def add_remove_favorite(self, request, pk=None):

        recipe = self.get_object()

        if request.method == 'POST':
            if Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists():

                return Response(
                    {'errors': 'Рецепт уже добавлен в избранное'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Favorite.objects.create(
                user=request.user,
                recipe=recipe
            )

            serializer = self.get_serializer(recipe)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            )

            if not favorite.exists():
                return Response(
                    {'errors': 'Рецепта нет в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            favorite.delete()

            return Response(
                status=status.HTTP_204_NO_CONTENT
            )


class GetIngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для ингридиентов.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientsSearchFilter,)
    search_fields = ('^name',)
    permission_classes = [AllowAny]
