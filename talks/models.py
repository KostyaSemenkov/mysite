from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TalkQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def upcoming(self):
        return self.published().filter(status='upcoming')

    def past(self):
        return self.published().filter(status='past')


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
    status = models.CharField('Статус', max_length=10,
                              choices=[('upcoming', 'Анонс'), ('past', 'Состоялось')],
                              default='past')
    registration_url = models.URLField('Ссылка регистрации', blank=True,
                                       help_text='Для анонсов: куда регистрироваться')
    is_published = models.BooleanField('Опубликован', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    objects = TalkQuerySet.as_manager()

    class Meta:
        verbose_name = 'Выступление'
        verbose_name_plural = 'Выступления'
        ordering = ['-status', '-spoke_at', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('talks:talk_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title


class CalendarEvent(models.Model):
    """Событие в календаре выступлений: доклад, участие, CFP-дедлайн, личное."""

    KINDS = [
        ('talk', 'Доклад'),
        ('attend', 'Участие'),
        ('cfp', 'CFP-дедлайн'),
        ('personal', 'Личное'),
    ]

    date = models.DateField('Дата')
    time = models.TimeField('Время', null=True, blank=True)
    kind = models.CharField('Тип', max_length=10, choices=KINDS, default='talk')
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Описание', blank=True, help_text='Несколько строк текста')
    link1_url = models.URLField('Ссылка 1', blank=True)
    link1_label = models.CharField('Подпись ссылки 1', max_length=120, blank=True)
    link2_url = models.URLField('Ссылка 2', blank=True)
    link2_label = models.CharField('Подпись ссылки 2', max_length=120, blank=True)
    talk = models.ForeignKey(Talk, verbose_name='Выступление', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='calendar_events')
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Событие календаря'
        verbose_name_plural = 'Календарь'
        ordering = ['date', 'time']

    def __str__(self):
        return f'{self.date} · {self.title}'
