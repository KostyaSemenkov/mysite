from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Topic(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Слаг', max_length=220, unique=True, blank=True)
    body = models.TextField('Первое сообщение', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Автор',
                                   null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='topics')
    is_pinned = models.BooleanField('Закреплена', default=False)
    is_closed = models.BooleanField('Закрыта для комментариев', default=False)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы форума'
        ordering = ['-is_pinned', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('forum:topic_detail', kwargs={'slug': self.slug})

    def visible_comments(self):
        return self.comments.filter(is_approved=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    topic = models.ForeignKey(Topic, verbose_name='Тема', on_delete=models.CASCADE,
                              related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Автор',
                               null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='comments')
    guest_name = models.CharField('Имя гостя', max_length=120, blank=True)
    body = models.TextField('Комментарий')
    is_approved = models.BooleanField('Одобрен', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']

    @property
    def display_name(self):
        return self.author.username if self.author else (self.guest_name or 'Гость')

    def __str__(self):
        return f'{self.display_name}: {self.body[:50]}'
