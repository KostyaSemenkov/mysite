from django.db import models
from django.conf import settings

COMPANIES = [('kimi', 'Kimi'), ('zai', 'Z.ai'), ('qwen', 'Qwen'), ('deepseek', 'DeepSeek')]

class NewsSource(models.Model):
    company = models.CharField('Компания', max_length=20, choices=COMPANIES, unique=True)
    enabled = models.BooleanField('Собирать новости', default=True)
    initialized = models.BooleanField(default=False)
    seen_keys = models.JSONField(default=list, editable=False)
    last_checked = models.DateTimeField('Последняя проверка', null=True, blank=True)
    last_success = models.DateTimeField('Последняя успешная проверка', null=True, blank=True)
    last_error = models.TextField('Ошибка', blank=True)
    class Meta:
        verbose_name = 'источник новостей'
        verbose_name_plural = 'Источники китайских нейросетей'
    def __str__(self): return self.get_company_display()

class IncomingNews(models.Model):
    STATES = [('waiting','Ожидает русского изложения'), ('review','Готово к проверке'), ('changed','Источник изменился'), ('published','Опубликовано'), ('rejected','Отклонено')]
    EVENTS = [('model','Модель'), ('feature','Новая функция'), ('api','API и цены')]
    source = models.ForeignKey(NewsSource, on_delete=models.PROTECT, verbose_name='Источник')
    source_key = models.CharField(max_length=300, editable=False)
    source_url = models.URLField('Официальная публикация', max_length=1000)
    original_title = models.CharField('Заголовок оригинала', max_length=500)
    original_text = models.TextField('Текущий оригинал')
    previous_text = models.TextField('Предыдущая версия оригинала', blank=True)
    source_date = models.DateTimeField('Дата у источника')
    content_hash = models.CharField(max_length=64, editable=False)
    summary_source_hash = models.CharField(max_length=64, blank=True, editable=False)
    title_ru = models.CharField('Заголовок на русском', max_length=220, blank=True)
    summary_ru = models.TextField('Краткое описание', max_length=400, blank=True)
    body_ru = models.TextField('Короткое изложение на русском', blank=True)
    event = models.CharField('Тип события', max_length=20, choices=EVENTS, default='model')
    status = models.CharField('Статус', max_length=20, choices=STATES, default='waiting')
    editor_note = models.TextField('Заметка редактора', blank=True)
    fetched_at = models.DateTimeField('Впервые получено', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)
    publication = models.OneToOneField('Publication', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Публикация')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-source_date']
        constraints = [models.UniqueConstraint(fields=['source','source_key'], name='unique_official_news')]
        verbose_name = 'входящая новость'
        verbose_name_plural = 'Китайские нейросети — входящие новости'
    def __str__(self): return self.title_ru or self.original_title

class ImportRun(models.Model):
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    created = models.PositiveIntegerField(default=0)
    changed = models.PositiveIntegerField(default=0)
    skipped = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'проверка источника'
        verbose_name_plural = 'Журнал сбора новостей'
