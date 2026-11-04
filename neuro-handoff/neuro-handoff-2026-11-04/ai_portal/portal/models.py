from django.db import models
from django.urls import reverse
from django.utils import timezone

class Publication(models.Model):
    KINDS = [('news','Новость'),('article','Статья')]
    TOPICS = [('tools','Инструменты'),('business','ИИ в работе'),('code','Программирование'),('creative','Изображения и видео')]
    company = models.CharField('Китайская нейросеть', max_length=20, choices=[('kimi','Kimi'),('zai','Z.ai'),('qwen','Qwen'),('deepseek','DeepSeek')], blank=True, db_index=True)
    title = models.CharField('Заголовок',max_length=220)
    slug = models.SlugField('Адрес',unique=True)
    kind = models.CharField('Тип',max_length=20,choices=KINDS,default='news')
    topic = models.CharField('Тема',max_length=20,choices=TOPICS)
    summary = models.TextField('Краткое описание',max_length=400)
    body = models.TextField('Текст')
    author = models.CharField('Автор',max_length=100,default='Редакция НЕЙРО')
    image_url = models.URLField('Обложка (URL)',blank=True)
    source_url = models.URLField('Источник',blank=True)
    published = models.BooleanField('Опубликовано',default=False)
    demo = models.BooleanField('Демонстрационный материал',default=False)
    featured = models.BooleanField('На главной',default=False)
    published_at = models.DateTimeField('Дата публикации',default=timezone.now)
    class Meta:
        ordering = ['-published_at']
        verbose_name = 'публикация'
        verbose_name_plural = 'публикации'
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('publication',args=[self.slug])

class Course(models.Model):
    LEVELS = [('beginner','Для начинающих'),('intermediate','Средний уровень')]
    title = models.CharField('Название',max_length=200)
    slug = models.SlugField(unique=True)
    provider = models.CharField('Организатор',max_length=120)
    summary = models.TextField('Описание')
    audience = models.TextField('Кому подходит')
    program = models.TextField('Программа (один модуль на строку)')
    level = models.CharField('Уровень',max_length=20,choices=LEVELS)
    direction = models.CharField('Направление',max_length=20,choices=Publication.TOPICS)
    duration = models.CharField('Длительность',max_length=80)
    price = models.PositiveIntegerField('Цена, ₽',default=0)
    format = models.CharField('Формат',max_length=80,default='Онлайн · в своём темпе')
    external_url = models.URLField('Ссылка на обучение',blank=True)
    checked_at = models.DateField('Условия проверены',default=timezone.localdate)
    published = models.BooleanField('Опубликовано',default=False)
    demo = models.BooleanField('Демонстрационный курс',default=False)
    class Meta:
        ordering = ['price','title']
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('course',args=[self.slug])

from .news_models import NewsSource, IncomingNews, ImportRun
