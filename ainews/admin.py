from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils import timezone

from .models import Course, ImportRun, IncomingNews, NewsSource, Publication
from .news.service import mark_ready, publish, reject, revision


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'kind', 'published', 'featured', 'published_at')
    list_filter = ('published', 'kind', 'company', 'topic')
    search_fields = ('title', 'summary', 'body')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'level', 'price', 'published')
    list_filter = ('published', 'level', 'direction')
    search_fields = ('title', 'provider', 'summary')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ('company', 'enabled', 'last_checked', 'last_success', 'last_error')
    list_editable = ('enabled',)


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ('source', 'started_at', 'created', 'changed', 'skipped', 'error')
    list_filter = ('source',)
    readonly_fields = ('source', 'started_at', 'finished_at', 'created', 'changed',
                       'skipped', 'error')


@admin.register(IncomingNews)
class IncomingNewsAdmin(admin.ModelAdmin):
    list_display = ('original_title', 'source', 'status', 'event', 'source_date', 'preview_link')
    list_filter = ('status', 'source', 'event')
    search_fields = ('original_title', 'title_ru', 'original_text')
    readonly_fields = ('source', 'source_key', 'source_url', 'original_title',
                       'original_text', 'previous_text', 'source_date',
                       'content_hash', 'fetched_at', 'updated_at')
    actions = ['action_approve', 'action_reject']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/preview/', self.admin_site.admin_view(self.preview_view),
                 name='ainews_incomingnews_preview'),
            path('<int:pk>/ready/', self.admin_site.admin_view(self.ready_view),
                 name='ainews_incomingnews_ready'),
            path('<int:pk>/approve/', self.admin_site.admin_view(self.approve_view),
                 name='ainews_incomingnews_approve'),
            path('<int:pk>/reject/', self.admin_site.admin_view(self.reject_view),
                 name='ainews_incomingnews_reject'),
        ]
        return custom + urls

    @admin.display(description='Предпросмотр')
    def preview_link(self, obj):
        return format_html('<a href="{}">Открыть</a>',
                           reverse('admin:ainews_incomingnews_preview', args=[obj.pk]))

    def preview_view(self, request, pk):
        """Оригинал рядом с русской версией и кнопки проверки.

        В каждой кнопке — ревизия новости: если источник или текст изменились,
        пока страница была открыта, действие не выполняется (см. news.service).
        """
        obj = get_object_or_404(IncomingNews, pk=pk)
        return render(request, 'admin/ainews/preview.html', {'obj': obj, 'rev': revision(obj)})

    def _review(self, request, pk, action, success_message):
        """POST-обработчик кнопок проверки; ошибки сервиса показываются сообщением."""
        obj = get_object_or_404(IncomingNews, pk=pk)
        if request.method == 'POST':
            try:
                action(obj, request.POST.get('rev') or '')
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
            else:
                messages.success(request, success_message)
        return redirect('admin:ainews_incomingnews_changelist')

    def ready_view(self, request, pk):
        return self._review(request, pk, mark_ready, 'Русский текст отмечен готовым к проверке.')

    def approve_view(self, request, pk):
        return self._review(request, pk, lambda obj, rev: publish(obj, request.user, rev),
                            'Новость опубликована.')

    def reject_view(self, request, pk):
        return self._review(request, pk, reject, 'Новость отклонена.')

    @admin.action(description='Одобрить и опубликовать')
    def action_approve(self, request, queryset):
        for obj in queryset:
            if obj.status in ('review', 'waiting', 'changed'):
                publish(obj, request.user)

    @admin.action(description='Отклонить')
    def action_reject(self, request, queryset):
        for obj in queryset:
            reject(obj)
