from django.db import models


class ContactRequest(models.Model):
    name = models.CharField('Имя', max_length=120)
    email = models.EmailField('Email')
    message = models.TextField('Сообщение')
    created_at = models.DateTimeField('Получено', auto_now_add=True)
    is_processed = models.BooleanField('Обработано', default=False)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.email}'


class Subscriber(models.Model):
    email = models.EmailField('Email', unique=True)
    created_at = models.DateTimeField('Подписан', auto_now_add=True)

    class Meta:
        verbose_name = 'Подписчик'
        verbose_name_plural = 'Подписчики'
        ordering = ['-created_at']

    def __str__(self):
        return self.email
