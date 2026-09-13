from django.db import models


class Profile(models.Model):
    """Singleton-модель: данные о владельце для главной и страницы «Обо мне»."""

    name = models.CharField('Имя', max_length=120)
    tagline = models.CharField('Кто вы (одной строкой)', max_length=200,
                               help_text='Например: Backend-разработчик и автор технического блога')
    about = models.TextField('Обо мне')
    photo = models.ImageField('Фото', upload_to='profile/', blank=True, null=True)
    email = models.EmailField('Email', blank=True)
    github = models.URLField('GitHub', blank=True)
    linkedin = models.URLField('LinkedIn', blank=True)
    telegram = models.URLField('Telegram', blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профиль'

    def __str__(self):
        return self.name
