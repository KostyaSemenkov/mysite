from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class ProjectQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Project(models.Model):
    title = models.CharField('Название', max_length=200)
    slug = models.SlugField('Слаг', max_length=220, unique=True, blank=True)
    description = models.TextField('Описание')
    tech_stack = models.CharField('Технологии', max_length=300, blank=True,
                                  help_text='Через запятую: Python, Django, PostgreSQL')
    url = models.URLField('Демо/сайт', blank=True)
    repo_url = models.URLField('Репозиторий', blank=True)
    image = models.ImageField('Скриншот', upload_to='projects/', blank=True, null=True)
    order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликован', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['order', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title
