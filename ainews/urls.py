from django.urls import path

from . import views
from .feeds import AIRSSFeed

app_name = 'ainews'

urlpatterns = [
    path('', views.ai_index, name='index'),
    path('courses/', views.courses, name='courses'),
    path('courses/<slug:slug>/', views.course_detail, name='course'),
    path('read/<slug:slug>/', views.publication, name='publication'),
    path('rss/', AIRSSFeed(), name='rss'),
]
