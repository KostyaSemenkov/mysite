from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


class Testimonial(models.Model):
    """Отзыв для стены на главной; короткая цитата + полная история в попапе."""

    author = models.CharField('Автор', max_length=120)
    role = models.CharField('Кто он', max_length=160, blank=True,
                            help_text='Например: QA-лид, компания X')
    quote = models.CharField('Короткая цитата', max_length=300)
    full_text = models.TextField('Полная история', blank=True,
                                 help_text='Показывается в попапе «Читать полностью»')
    photo = models.ImageField('Фото', upload_to='testimonials/', blank=True, null=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликован', default=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.author}: {self.quote[:40]}…'


class FaqItem(models.Model):
    question = models.CharField('Вопрос', max_length=300)
    answer = models.TextField('Ответ')
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликован', default=True)

    class Meta:
        verbose_name = 'Вопрос FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['order', 'id']

    def __str__(self):
        return self.question


class Favorite(models.Model):
    """Избранное пользователя: пост, проект или выступление (generic FK)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='favorites')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=36)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'В избранном'
        verbose_name_plural = 'Избранное'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'content_type', 'object_id'],
                                    name='uniq_favorite'),
        ]

    def __str__(self):
        return f'{self.user} → {self.content_object}'


class UsefulFile(models.Model):
    """Чек-лист/шаблон из раздела «Полезности» — лид-магнит для подписки."""

    title = models.CharField('Название', max_length=200)
    description = models.CharField('Краткое описание', max_length=300, blank=True)
    file = models.FileField('Файл', upload_to='useful/')
    downloads = models.PositiveIntegerField('Скачиваний', default=0)
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликован', default=True)

    class Meta:
        verbose_name = 'Полезный файл'
        verbose_name_plural = 'Полезности'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    """Вопрос мини-тренажёра тестирования."""

    order = models.PositiveSmallIntegerField('Порядок', default=0)
    mode = models.CharField('Режим', max_length=10,
                            choices=[('base', 'База'), ('interview', 'Симулятор')],
                            default='base')
    question = models.CharField('Вопрос', max_length=400)
    option_a = models.CharField('Вариант A', max_length=250)
    option_b = models.CharField('Вариант B', max_length=250)
    option_c = models.CharField('Вариант C', max_length=250)
    option_d = models.CharField('Вариант D', max_length=250)
    correct = models.CharField('Правильный', max_length=1,
                               choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])
    explanation = models.TextField('Разбор', blank=True)

    class Meta:
        verbose_name = 'Вопрос квиза'
        verbose_name_plural = 'Вопросы квиза'
        ordering = ['order', 'id']

    def __str__(self):
        return self.question[:60]


class PathStep(models.Model):
    """Ступень «Пути тестировщика»."""

    order = models.PositiveSmallIntegerField('Порядок', default=0)
    title = models.CharField('Название', max_length=120)
    description = models.CharField('Описание', max_length=300, blank=True)

    class Meta:
        verbose_name = 'Ступень пути'
        verbose_name_plural = 'Путь тестировщика'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class PathItem(models.Model):
    """Пункт ступени: ссылка на материал сайта (статья/квиз/чек-лист/...)."""

    KINDS = [
        ('post', 'Статья'),
        ('quiz', 'Квиз'),
        ('checklist', 'Чек-лист'),
        ('forum', 'Форум'),
        ('talk', 'Выступление'),
        ('external', 'Внешняя ссылка'),
    ]

    step = models.ForeignKey(PathStep, verbose_name='Ступень',
                             on_delete=models.CASCADE, related_name='items')
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    title = models.CharField('Заголовок', max_length=200)
    kind = models.CharField('Тип', max_length=10, choices=KINDS, default='post')
    url = models.CharField('Ссылка', max_length=500,
                           help_text='Внутренний путь (/blog/...) или внешний URL')

    class Meta:
        verbose_name = 'Пункт пути'
        verbose_name_plural = 'Пункты пути'
        ordering = ['step__order', 'order', 'id']

    def __str__(self):
        return self.title


class UserPathProgress(models.Model):
    """Отметка «пройдено» у пункта пути."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='path_progress')
    item = models.ForeignKey(PathItem, on_delete=models.CASCADE,
                             related_name='progress')
    done_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Прогресс пути'
        verbose_name_plural = 'Прогресс пути'
        unique_together = ('user', 'item')

    def __str__(self):
        return f'{self.user} · {self.item}'


class QuizAttempt(models.Model):
    """Попытка прохождения квиза/симулятора."""

    MODES = [('base', 'База'), ('interview', 'Симулятор собеседования')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='quiz_attempts')
    mode = models.CharField('Режим', max_length=10, choices=MODES, default='base')
    score = models.PositiveSmallIntegerField('Результат, %')
    total = models.PositiveSmallIntegerField('Вопросов', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Попытка квиза'
        verbose_name_plural = 'Попытки квиза'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_mode_display()} · {self.score}%'
