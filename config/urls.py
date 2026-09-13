from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from contacts import views as contact_views
from pages import views as page_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', page_views.home, name='home'),
    path('about/', page_views.about, name='about'),
    path('blog/', include('blog.urls')),
    path('projects/', include('projects.urls')),
    path('contacts/', include('contacts.urls')),
    path('subscribe/', contact_views.subscribe, name='subscribe'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
