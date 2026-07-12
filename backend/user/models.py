from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    avatar = models.ImageField(upload_to='avatars/')

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
