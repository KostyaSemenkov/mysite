from django.urls import path

from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.topic_list, name='topic_list'),
    path('new/', views.new_topic, name='new_topic'),
    path('<str:slug>/', views.topic_detail, name='topic_detail'),
    path('<str:slug>/comment/', views.add_comment, name='add_comment'),
]
