from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField

from .models import (Ingredient, Recipe, RecipeIngredient,
                     Tag, User)


class SignupSerializer(serializers.ModelSerializer):
    """
    Сериализатор регистрации пользователя.
    """
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class GetUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для пользовательских данных для метода GET.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        return getattr(obj, 'is_subscribed', False)


class RecipeSubscriptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class PostSubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор получения сведений о подписке на пользователя.
    """
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(read_only=True)
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        return getattr(obj, 'is_subscribed', False)

    def get_recipes(self, obj):
        recipes = obj.recipes.all()

        limit = self.context['request'].query_params.get('recipes_limit')

        if limit:
            try:
                recipes = recipes[:int(limit)]
            except ValueError:
                pass

        return RecipeSubscriptionSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class PutAvatarSerializer(serializers.ModelSerializer):
    """
    Сериализатор редактирования аватара пользователя.
    """
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор изменения пароля.
    """
    new_password = serializers.CharField(required=True, write_only=True)
    current_password = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user

        if not user.check_password(value):
            raise serializers.ValidationError({'error': 'Неверный пароль'})

        return value

    def validate(self, attrs):
        current_password = attrs.get('old_password')
        new_password = attrs.get('new_password')

        if current_password == new_password:
            raise serializers.ValidationError(
                {'error': 'Новый пароль совпадает со старым'}
            )

        return attrs

    def save(self):
        request = self.context.get('request')
        user = request.user
        user.set_password(self.validated_data['new_password'])
        user.save()

        return user


class GetTagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для тегов.
    """
    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug',
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True,
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class RecipesGetSerializer(serializers.ModelSerializer):
    """
    Сериализатор для get-запросов к ресурсу recipes.
    """

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = GetUserSerializer(read_only=True)
    tags = GetTagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        return getattr(obj, 'is_favorited', False)

    def get_is_in_shopping_cart(self, obj):
        return getattr(obj, 'is_in_shopping_cart', False)


class RecipesPostSerializer(serializers.ModelSerializer):
    """
    Сериализатор для post-запросов к ресурсу recipes.
    """
    image = Base64ImageField(
        required=True,
        allow_null=False,
    )
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        required=True,
        allow_empty=False,
    )
    author = GetUserSerializer(read_only=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
            'author',
        )

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Изображение обязательно.'
            )

        return value

    def to_representation(self, instance):

        return RecipesGetSerializer(
            instance,
            context=self.context
        ).data

    @staticmethod
    def create_recipe_ingredients(recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=item['ingredient'],
                    amount=item['amount']
                )
                for item in ingredients
            ]
        )

    def validate(self, attrs):
        if self.instance and 'recipe_ingredients' not in attrs:
            raise serializers.ValidationError(
                {
                    'tags': 'Поле обязательно.'
                }
            )

        if self.instance and 'tags' not in attrs:
            raise serializers.ValidationError(
                {
                    'ingredients': 'Поле обязательно.'
                }
            )

        ingredients = attrs.get('recipe_ingredients')

        if ingredients:
            ingredient_ids = [
                ingredient['ingredient'].id
                for ingredient in ingredients
            ]

            if len(ingredient_ids) != len(set(ingredient_ids)):
                raise serializers.ValidationError(
                    {
                        'ingredients': 'Ингредиенты не должны повторяться.'
                    }
                )

        tags = attrs.get('tags')

        if tags:
            tag_ids = [
                tag.id
                for tag in tags
            ]

            if len(tag_ids) != len(set(tag_ids)):
                raise serializers.ValidationError(
                    {
                        'tags': 'Теги не должны повторяться.'
                    }
                )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('recipe_ingredients')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(
            **validated_data
        )

        recipe.tags.set(tags)

        self.create_recipe_ingredients(
            recipe,
            ingredients
        )

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('recipe_ingredients')
        tags = validated_data.pop('tags')

        instance = super().update(instance, validated_data)

        instance.tags.set(tags)

        instance.recipe_ingredients.all().delete()

        self.create_recipe_ingredients(
            instance,
            ingredients
        )

        return instance


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для корзины пользователя.
    """
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор ресурса ingredients
    """

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class GetTokenSerializer(serializers.ModelSerializer):
    """
    Сериализатор получения токена.
    """
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('email', 'password')
