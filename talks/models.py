from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TalkQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Talk(models.Model):
    title = models.CharField('Название', max_length=200)
    slug = models.SlugField('Слаг', max_length=220, unique=True, blank=True)
    description = models.TextField('Описание')
    event = models.CharField('Мероприятие', max_length=200, blank=True,
                             help_text='Например: Heisenbug, SQADays, митап в офисе')
    video = models.FileField('Видеофайл', upload_to='talks/', blank=True, null=True,
                             help_text='MP4 или WebM играются в браузере напрямую; '
                                       'MOV/AVI лучше конвертировать в MP4')
    video_url = models.URLField('Ссылка на видео', blank=True,
                                help_text='YouTube/VK/ Rutube — если видео хостится снаружи')
    thumbnail = models.ImageField('Превью', upload_to='talks/thumbs/', blank=True, null=True)
    spoke_at = models.DateField('Дата выступления', null=True, blank=True)
    is_published = models.BooleanField('Опубликован', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    objects = TalkQuerySet.as_manager()

    class Meta:
        verbose_name = 'Выступление'
        verbose_name_plural = 'Выступления'
        ordering = ['-spoke_at', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('talks:talk_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title
