from django.contrib import admin
from .models import Publication, Course
@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['title','kind','topic','published','demo','published_at']
    list_filter = ['kind','topic','published','demo']
    search_fields = ['title','body']
    prepopulated_fields = {'slug':('title',)}
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title','provider','price','published','demo']
    list_filter = ['level','direction','published']
    search_fields = ['title','provider']
    prepopulated_fields = {'slug':('title',)}
admin.site.site_header = 'НЕЙРО · Редакция'
admin.site.site_title = 'НЕЙРО'

from . import news_admin
