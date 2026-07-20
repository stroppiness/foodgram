from django.contrib.auth.models import AbstractUser
from django.db import models

from api.constants import USER_NAME_MAX_LENGTH, USER_EMAIL_MAX_LENGTH


class User(AbstractUser):
    email = models.EmailField(
        max_length=USER_EMAIL_MAX_LENGTH,
        unique=True,
    )
    first_name = models.CharField(
        max_length=USER_NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        max_length=USER_NAME_MAX_LENGTH,
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        default=''
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [
        'username',
        'first_name',
        'last_name'
    ]

    class Meta:
        ordering = ['username']
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
