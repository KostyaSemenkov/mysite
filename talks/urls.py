from django.urls import path

from . import views

app_name = 'talks'

urlpatterns = [
    path('', views.talk_list, name='talk_list'),
    path('calendar/', views.calendar_page, name='calendar'),
    path('calendar/feed.ics', views.ical_feed, name='ical_feed'),
    path('<str:slug>/', views.talk_detail, name='talk_detail'),
]
