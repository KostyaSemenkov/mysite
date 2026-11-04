from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

COMPANIES = [('kimi', 'Kimi'), ('zai', 'Z.ai'), ('qwen', 'Qwen'), ('deepseek', 'DeepSeek')]


class Publication(models.Model):
    """Новость/статья раздела «ИИ-новости»."""

    KINDS = [('news', 'Новость'), ('article', 'Статья')]
    TOPICS = [('tools', 'Инструменты'), ('business', 'ИИ в работе'),
              ('code', 'Программирование'), ('creative', 'Изображения и видео')]

    company = models.CharField('Компания', max_length=20, choices=COMPANIES,
                               blank=True, db_index=True)
    title = models.CharField('Заголовок', max_length=220)
    slug = models.SlugField('Слаг', unique=True)
    kind = models.CharField('Тип', max_length=20, choices=KINDS, default='news')
    topic = models.CharField('Тема', max_length=20, choices=TOPICS, default='tools')
    summary = models.TextField('Краткое описание', max_length=400, blank=True)
    body = models.TextField('Текст')
    author = models.CharField('Автор', max_length=100, default='Редакция')
    image_url = models.URLField('Обложка (URL)', blank=True)
    source_url = models.URLField('Источник', blank=True)
    published = models.BooleanField('Опубликовано', default=False)
    demo = models.BooleanField('Демонстрационный материал', default=False)
    featured = models.BooleanField('На главной раздела', default=False)
    published_at = models.DateTimeField('Дата публикации', default=timezone.now)

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'ИИ-публикация'
        verbose_name_plural = 'ИИ-публикации'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('ainews:publication', args=[self.slug])


class Course(models.Model):
    """Курс по ИИ в каталоге."""

    LEVELS = [('beginner', 'Для начинающих'), ('intermediate', 'Средний уровень')]

    title = models.CharField('Название', max_length=200)
    slug = models.SlugField(unique=True)
    provider = models.CharField('Организатор', max_length=120)
    summary = models.TextField('Описание')
    audience = models.TextField('Кому подходит', blank=True)
    program = models.TextField('Программа (один модуль на строку)', blank=True)
    level = models.CharField('Уровень', max_length=20, choices=LEVELS,
                             default='beginner')
    direction = models.CharField('Направление', max_length=20,
                                 choices=Publication.TOPICS, default='tools')
    duration = models.CharField('Длительность', max_length=80, blank=True)
    price = models.PositiveIntegerField('Цена, ₽', default=0)
    fmt = models.CharField('Формат', max_length=80, default='Онлайн · в своём темпе')
    external_url = models.URLField('Ссылка на обучение', blank=True)
    checked_at = models.DateField('Условия проверены', default=timezone.localdate)
    published = models.BooleanField('Опубликовано', default=False)
    demo = models.BooleanField('Демонстрационный курс', default=False)

    class Meta:
        ordering = ['price', 'title']
        verbose_name = 'ИИ-курс'
        verbose_name_plural = 'ИИ-курсы'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('ainews:course', args=[self.slug])

    def program_lines(self):
        return [l.strip() for l in self.program.split('\n') if l.strip()]


class NewsSource(models.Model):
    """Источник официальных новостей китайской ИИ-компании."""

    company = models.CharField('Компания', max_length=20, choices=COMPANIES, unique=True)
    enabled = models.BooleanField('Собирать новости', default=True)
    initialized = models.BooleanField(default=False)
    seen_keys = models.JSONField(default=list, editable=False)
    last_checked = models.DateTimeField('Последняя проверка', null=True, blank=True)
    last_success = models.DateTimeField('Последний успех', null=True, blank=True)
    last_error = models.TextField('Ошибка', blank=True)

    class Meta:
        verbose_name = 'источник ИИ-новостей'
        verbose_name_plural = 'Источники ИИ-новостей'

    def __str__(self):
        return self.get_company_display()


class IncomingNews(models.Model):
    """Входящая новость в редакционной очереди."""

    STATES = [
        ('waiting', 'Ожидает изложения'),
        ('review', 'Готово к проверке'),
        ('changed', 'Источник изменился'),
        ('published', 'Опубликовано'),
        ('rejected', 'Отклонено'),
    ]
    EVENTS = [('model', 'Модель'), ('feature', 'Новая функция'), ('api', 'API и цены')]

    source = models.ForeignKey(NewsSource, on_delete=models.PROTECT,
                               verbose_name='Источник')
    source_key = models.CharField(max_length=300, editable=False)
    source_url = models.URLField('Официальная публикация', max_length=1000)
    original_title = models.CharField('Заголовок оригинала', max_length=500)
    original_text = models.TextField('Текущий оригинал')
    previous_text = models.TextField('Предыдущая версия', blank=True)
    source_date = models.DateTimeField('Дата у источника')
    content_hash = models.CharField(max_length=64, editable=False)
    summary_source_hash = models.CharField(max_length=64, blank=True, editable=False)
    title_ru = models.CharField('Заголовок на русском', max_length=220, blank=True)
    summary_ru = models.TextField('Краткое описание', max_length=400, blank=True)
    body_ru = models.TextField('Изложение на русском', blank=True)
    event = models.CharField('Тип события', max_length=20, choices=EVENTS,
                             default='model')
    status = models.CharField('Статус', max_length=20, choices=STATES,
                              default='waiting')
    editor_note = models.TextField('Заметка редактора', blank=True)
    fetched_at = models.DateTimeField('Впервые получено', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)
    publication = models.OneToOneField(Publication, on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       verbose_name='Публикация')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-source_date']
        constraints = [
            models.UniqueConstraint(fields=['source', 'source_key'],
                                    name='unique_official_news'),
        ]
        verbose_name = 'входящая ИИ-новость'
        verbose_name_plural = 'ИИ-очередь новостей'

    def __str__(self):
        return self.title_ru or self.original_title


class ImportRun(models.Model):
    """Журнал запусков сборщика."""

    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    created = models.PositiveIntegerField(default=0)
    changed = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'запуск сборщика'
        verbose_name_plural = 'Журнал сборщика ИИ-новостей'
