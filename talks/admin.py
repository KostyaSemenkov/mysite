from django.contrib import admin

from .models import CalendarEvent, Talk


@admin.register(Talk)
class TalkAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'spoke_at', 'is_published')
    list_filter = ('is_published', 'spoke_at')
    search_fields = ('title', 'description', 'event')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'spoke_at'


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('date', 'time', 'kind', 'title')
    list_filter = ('kind', 'date')
    date_hierarchy = 'date'
    search_fields = ('title', 'text')
    autocomplete_fields = []
