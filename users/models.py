from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', 'Клиент'
        MASTER = 'MASTER', 'Мастер'
        ADMIN = 'ADMIN', 'Администратор'

    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name='Роль'
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Номер телефона'
    )

    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"