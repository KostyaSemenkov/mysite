from django.urls import path

from . import views

app_name = 'contacts'

urlpatterns = [
    path('', views.contact_page, name='contact'),
    path('submit/', views.contact_submit, name='contact_submit'),
]
