from django.urls import path

from . import views

app_name = 'talks'

urlpatterns = [
    path('', views.talk_list, name='talk_list'),
    path('<str:slug>/', views.talk_detail, name='talk_detail'),
]
