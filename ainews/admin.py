from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect, render
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
    list_display = ('original_title', 'source', 'status', 'event', 'source_date')
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

    def preview_view(self, request, pk):
        obj = IncomingNews.objects.get(pk=pk)
        return render(request, 'admin/ainews/preview.html', {'obj': obj})

    def ready_view(self, request, pk):
        obj = IncomingNews.objects.get(pk=pk)
        if request.method == 'POST' and revision(obj) == request.POST.get('rev'):
            mark_ready(obj)
        return redirect('admin:ainews_incomingnews_changelist')

    def approve_view(self, request, pk):
        obj = IncomingNews.objects.get(pk=pk)
        if request.method == 'POST' and revision(obj) == request.POST.get('rev'):
            publish(obj, request.user)
        return redirect('admin:ainews_incomingnews_changelist')

    def reject_view(self, request, pk):
        obj = IncomingNews.objects.get(pk=pk)
        if request.method == 'POST' and revision(obj) == request.POST.get('rev'):
            reject(obj)
        return redirect('admin:ainews_incomingnews_changelist')

    @admin.action(description='Одобрить и опубликовать')
    def action_approve(self, request, queryset):
        for obj in queryset:
            if obj.status in ('review', 'waiting', 'changed'):
                publish(obj, request.user)

    @admin.action(description='Отклонить')
    def action_reject(self, request, queryset):
        for obj in queryset:
            reject(obj)
