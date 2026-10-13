from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Post(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Слаг', max_length=220, unique=True, blank=True)
    excerpt = models.CharField('Краткое описание', max_length=300, blank=True,
                               help_text='Показывается в списке постов и в мета-описании')
    content = models.TextField('Текст', help_text='Поддерживается Markdown-подобная разметка или чистый HTML')
    cover = models.ImageField('Обложка', upload_to='blog/', blank=True, null=True)
    tags = models.CharField('Теги', max_length=200, blank=True,
                            help_text='Через запятую: Python, Django, DevOps')
    is_published = models.BooleanField('Опубликован', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @property
    def reading_minutes(self):
        words = len(self.content.split())
        return max(1, round(words / 180))

    def __str__(self):
        return self.title


class GuestPostSubmission(models.Model):
    """Гостевой пост от зарегистрированного пользователя — на премодерации."""

    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('approved', 'Опубликован'),
        ('rejected', 'Отклонён'),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Автор',
                               on_delete=models.CASCADE, related_name='guest_posts')
    title = models.CharField('Заголовок', max_length=200)
    excerpt = models.CharField('Краткое описание', max_length=300, blank=True)
    content = models.TextField('Текст')
    tags = models.CharField('Теги', max_length=200, blank=True)
    status = models.CharField('Статус', max_length=10,
                              choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('Отправлен', auto_now_add=True)

    class Meta:
        verbose_name = 'Гостевой пост'
        verbose_name_plural = 'Гостевые посты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author.username}: {self.title}'
