from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from contacts import views as contact_views
from forum import views as forum_views
from pages import views as page_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', page_views.home, name='home'),
    path('about/', page_views.about, name='about'),
    path('blog/', include('blog.urls')),
    path('projects/', include('projects.urls')),
    path('contacts/', include('contacts.urls')),
    path('talks/', include('talks.urls')),
    path('forum/', include('forum.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', forum_views.register, name='register'),
    path('subscribe/', contact_views.subscribe, name='subscribe'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
