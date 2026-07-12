import pyshorteners
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientsSearchFilter, RecipeFilter
from .models import Ingredient, Recipe, Subscription, Tag, User
from .pagination import CustomPagination
from .permissions import IsAuthor
from .serializers import (ChangePasswordSerializer, GetTagSerializer,
                          GetTokenSerializer, GetUserSerializer,
                          IngredientSerializer, ListUserSerializer,
                          PostSubscriptionSerializer, PutAvatarSerializer,
                          RecipesGetSerializer, RecipesPostSerializer,
                          ShoppingCartSerializer, SignupSerializer)


class SignUpView(CreateAPIView):
    """
    Вью для регистрации пользователя.
    """
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]


class GetUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPagination
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
        elif self.action in ('create', 'list'):
            return ListUserSerializer
        return GetUserSerializer

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
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.data)

        elif request.method == 'DELETE':
            request.user.avatar.delete()
            request.user.avatar = None
            request.user.save()

            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data,
                                         context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
    )
    def add_remove_subscription(self, request, pk=None):
        author = self.get_object()

        if request.method == 'POST':

            if request.user == author:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            subscription, created = Subscription.objects.get_or_create(
                user=request.user,
                author=author
            )

            if not created:
                return Response(status=status.HTTP_400_BAD_REQUEST)

            serializer = PostSubscriptionSerializer(
                author,
                context={'request': request}
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':

            deleted, _ = Subscription.objects.filter(
                user=request.user,
                author=author
            ).delete()

            if not deleted:
                return Response(
                    {'error': 'Ошибка удаления'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(status=status.HTTP_204_NO_CONTENT)


class GetSubstriptionViewset(viewsets.ModelViewSet):
    """
    Вьюсет для get-запроса ресурса subscription.
    """
    serializer_class = PostSubscriptionSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return User.objects.filter(
            subscribers__user=self.request.user
        )


class GetTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для ресурса Tags.
    """
    queryset = Tag.objects.all()
    serializer_class = GetTagSerializer
    permission_classes = [AllowAny]


class GetRecipesViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для ресурса Recipes.
    """
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
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
        if self.action in ('list', 'retrieve', 'get_link'):
            return [AllowAny()]

        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAuthor()]

        return [IsAuthenticated()]

    def get_serializer_class(self):

        if self.action in ('create', 'update', 'partial_update'):
            return RecipesPostSerializer

        if self.action in ('add_remove_shopping_cart', 'add_remove_favorite'):
            return ShoppingCartSerializer

        return RecipesGetSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        recipe = serializer.instance
        response_serializer = RecipesGetSerializer(
            recipe,
            context={'request': request}
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        response_serializer = RecipesGetSerializer(
            serializer.instance,
            context={'request': request}
        )

        return Response(response_serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()

        url = f'https://foodgrams.duckdns.org/recipes/{recipe.id}/'

        s = pyshorteners.Shortener()

        short_url = s.clckru.short(url)

        return Response({
            'short-link': short_url
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
    )
    def get_shopping_cart_link(self, request):
        shopping_cart = request.user.shopping_list.all()

        shopping_dict = {}

        for recipe in shopping_cart:
            for recipe_ingredient in recipe.recipe_ingredients.all():
                ingredient = recipe_ingredient.ingredient
                amount = recipe_ingredient.amount

                if ingredient not in shopping_dict:
                    shopping_dict[ingredient] = amount
                else:
                    shopping_dict[ingredient] += amount

        words = []

        for ingredient, amount in shopping_dict.items():
            words.append(
                f'{ingredient.name} - {amount} {ingredient.measurement_unit}'
            )

        text = '\n'.join(words)

        response = HttpResponse(text, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )

        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
    )
    def add_remove_shopping_cart(self, request, pk=None):

        recipe = self.get_object()

        if request.method == 'POST':
            if recipe.shopping_list.filter(id=request.user.id).exists():
                return Response(
                    {'errors': 'Рецепт уже добавлен в корзину'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            request.user.shopping_list.add(recipe)

            serializer = self.get_serializer(recipe)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not recipe.shopping_list.filter(id=request.user.id).exists():
                return Response(
                    {'errors': 'Рецепта нет в корзине'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            request.user.shopping_list.remove(recipe)
            return Response(status=204)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
    )
    def add_remove_favorite(self, request, pk=None):

        recipe = self.get_object()

        if request.method == 'POST':
            if recipe.favorited_by.filter(id=request.user.id).exists():
                return Response(
                    {'errors': 'Рецепт уже добавлен в избранное'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            recipe.favorited_by.add(request.user)

            serializer = self.get_serializer(recipe)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not recipe.favorited_by.filter(id=request.user.id).exists():
                return Response(
                    {'errors': 'Рецепта нет в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            recipe.favorited_by.remove(request.user)

            return Response(status=status.HTTP_204_NO_CONTENT)


class GetIngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для ингридиентов.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientsSearchFilter,)
    search_fields = ('^name',)
    permission_classes = [AllowAny]


class GetOrRemoveTokenViewSet(viewsets.ViewSet):
    """
    Вьюсет для создания и удаления токена.
    """
    @action(
        detail=False,
        methods=['post'],
        url_path='login',
        permission_classes=[AllowAny]
    )
    def token_login(self, request):
        serializer = GetTokenSerializer(data=request.data)

        if serializer.is_valid():

            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = get_object_or_404(User, email=email)

            if not user.check_password(password):
                return Response(
                    {'detail': 'Неверный email или пароль'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token, created = Token.objects.get_or_create(
                user=user
            )

            return Response({
                'auth_token': token.key
            })

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=['post'],
        url_path='logout',
        permission_classes=[IsAuthenticated]
    )
    def token_logout(self, request):
        request.user.auth_token.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
