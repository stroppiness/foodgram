from django.core.validators import RegexValidator
from django.db.models import Q
from rest_framework import serializers

from .fields import Base64ImageField
from .models import (Ingredient, Recipe, RecipeIngredient, Tag,
                     User)


class SignupSerializer(serializers.ModelSerializer):
    """
    Сериализатор регистрации пользователя.
    """
    username = serializers.CharField(
        max_length=150,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
            )
        ]
    )
    email = serializers.EmailField(max_length=254, required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
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

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')

        if User.objects.filter(
            Q(username=username) & ~Q(email=email)
            | ~Q(username=username) & Q(email=email)
        ).exists():

            raise serializers.ValidationError('Username или email существует')

        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ListUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор пользовательских данных для list и create.
    """
    username = serializers.CharField(
        max_length=150,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+\Z',
            )
        ]
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
        )


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
        user = self.context['request'].user

        if user.is_anonymous:
            return False

        return obj.subscribers.filter(user=user).exists()


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
    is_subscribed = serializers.SerializerMethodField()
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
        return obj.subscribers.filter(
            user=self.context['request'].user).exists()

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        recipes = obj.recipes.all()

        limit = self.context['request'].query_params.get('recipes_limit')
        if limit:
            recipes = recipes[:int(limit)]

        return RecipeSubscriptionSerializer(
            recipes,
            many=True,
            context=self.context
        ).data


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
    new_password = serializers.CharField(required=True, max_length=50)
    current_password = serializers.CharField(required=True, max_length=50)

    def validate_current_password(self, value):
        request = self.context.get('request')

        if not request.user.check_password(value):
            raise serializers.ValidationError('Неверный пароль')

        return value

    def validate(self, attrs):
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                'Новый пароль совпадает со старым')

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
        source='ingredient.measurement_unit.name',
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
        request = self.context.get('request')

        if not request or request.user.is_anonymous:
            return False

        return obj.favorited_by.filter(
            id=request.user.id
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')

        if not request or request.user.is_anonymous:
            return False

        return request.user.shopping_list.filter(pk=obj.pk).exists()


class RecipesPostSerializer(serializers.ModelSerializer):
    """
    Сериализатор для post-запросов к ресурсу recipes.
    """
    image = Base64ImageField(required=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        required=False,
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

    def validate(self, attrs):
        if self.instance and 'recipe_ingredients' not in attrs:
            raise serializers.ValidationError(
                {
                    'ingredients': 'Поле обязательно.'
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

    def create(self, validated_data):
        ingredients = validated_data.pop('recipe_ingredients')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(
            **validated_data
        )

        recipe.tags.set(tags)

        for ingredient in ingredients:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            )

        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop(
            'recipe_ingredients',
            None
        )

        tags = validated_data.pop(
            'tags',
            None
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        if ingredients is not None:
            instance.recipe_ingredients.all().delete()

            for ingredient in ingredients:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient['ingredient'],
                    amount=ingredient['amount']
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
    measurement_unit = serializers.CharField(
        source='measurement_unit.name',
        read_only=True
    )

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
