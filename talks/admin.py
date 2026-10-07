from django.contrib import admin

from .models import Talk


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'spoke_at', 'is_published')
    list_filter = ('is_published', 'spoke_at')
    search_fields = ('title', 'description', 'event')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'spoke_at'
