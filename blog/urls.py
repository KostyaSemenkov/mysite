from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('guest-post/', views.guest_post, name='guest_post'),
    path('<str:slug>/', views.post_detail, name='post_detail'),
]
