from django.contrib import admin

from .models import Comment, Topic, TopicReaction


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'is_pinned', 'is_closed', 'is_resolved', 'created_at')
    list_editable = ('is_pinned', 'is_closed', 'is_resolved')
    search_fields = ('title', 'body')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'topic', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('body', 'guest_name')
    list_editable = ('is_approved',)
    actions = ['approve']

    @admin.action(description='Одобрить выбранные комментарии')
    def approve(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(TopicReaction)
class TopicReactionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'user', 'kind', 'created_at')
    list_filter = ('kind',)
