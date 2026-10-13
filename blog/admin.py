import os

from django.contrib import admin, messages
from django.core.mail import send_mass_mail
from django.utils.text import slugify

from contacts.models import Subscriber

from .models import GuestPostSubmission, Post


def _site_url():
    return os.environ.get('SITE_URL', 'https://lemurqa.ru').rstrip('/')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    actions = ('notify_subscribers',)

    @admin.action(description='Разослать подписчикам уведомление о постах')
    def notify_subscribers(self, request, queryset):
        if not os.environ.get('EMAIL_HOST'):
            self.message_user(request,
                              'SMTP не настроен: задайте EMAIL_HOST и учётные данные в .env',
                              level=messages.ERROR)
            return
        subs = list(Subscriber.objects.values_list('email', flat=True))
        if not subs:
            self.message_user(request, 'Подписчиков нет.', level=messages.WARNING)
            return
        from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@lemurqa.ru')
        site_name = os.environ.get('SITE_NAME', 'Лемурзильня тестировщика')
        emails = []
        for post in queryset.filter(is_published=True):
            body = (f'Новая статья на {_site_url()}:\n\n'
                    f'{post.title}\n\n{post.excerpt or post.content[:200]}\n\n'
                    f'Читать: {_site_url()}{post.get_absolute_url()}\n\n'
                    f'— {site_name}\nОтписаться — ответьте на это письмо.')
            for email in subs:
                emails.append((f'Новый пост: {post.title}', body, from_email, [email]))
        sent = send_mass_mail(emails, fail_silently=True)
        self.message_user(request, f'Отправлено писем: {sent} '
                                   f'({len(subs)} подписчиков × {queryset.count()} постов).')


@admin.register(GuestPostSubmission)
class GuestPostSubmissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('author', 'created_at')
    actions = ('approve_and_publish', 'reject')

    @admin.action(description='Одобрить и опубликовать как пост')
    def approve_and_publish(self, request, queryset):
        count = 0
        for s in queryset.filter(status='pending'):
            post = Post.objects.create(
                title=s.title,
                excerpt=s.excerpt or f'Гостевой пост от {s.author.username}',
                content=f'{s.content}\n\n— гостевой пост от {s.author.username}',
                tags=s.tags,
                is_published=True,
            )
            # уникальный слаг при совпадениях
            base = post.slug or slugify(s.title, allow_unicode=True)
            post.slug = base
            n = 0
            while Post.objects.filter(slug=post.slug).exclude(pk=post.pk).exists():
                n += 1
                post.slug = f'{base}-{n}'
            post.save()
            s.status = 'approved'
            s.save()
            count += 1
        self.message_user(request, f'Опубликовано гостевых постов: {count}')

    @admin.action(description='Отклонить')
    def reject(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'Отклонено: {updated}')
