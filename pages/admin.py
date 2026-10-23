from django.contrib import admin

from .models import FaqItem, Favorite, Profile, QuizQuestion, Testimonial, UsefulFile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'tagline', 'email')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author', 'role', 'order', 'is_published')
    list_editable = ('order', 'is_published')
    search_fields = ('author', 'quote', 'full_text')


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_published')
    list_editable = ('order', 'is_published')
    search_fields = ('question', 'answer')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'created_at')
    list_filter = ('content_type',)


@admin.register(UsefulFile)
class UsefulFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'downloads', 'order', 'is_published')
    list_editable = ('order', 'is_published')


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'order')
    list_editable = ('order',)
    search_fields = ('question',)
