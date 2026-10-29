from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.urls import include, path
from django.views.generic import TemplateView

from contacts import views as contact_views
from forum import views as forum_views
from pages import views as page_views
from pages.sitemaps import sitemaps
from pages.sso import boards_sso
from blog.feeds import LatestPostsFeed

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', page_views.home, name='home'),
    path('about/', page_views.about, name='about'),
    path('privacy/', page_views.privacy, name='privacy'),
    path('offer/', page_views.offer, name='offer'),
    path('waiting/', page_views.waiting_list, name='waiting_list'),
    path('search/', page_views.search, name='search'),
    path('useful/', page_views.useful_downloads, name='useful'),
    path('useful/<int:pk>/download/', page_views.download_file, name='useful_download'),
    path('services/', page_views.services, name='services'),
    path('quiz/', page_views.quiz, name='quiz'),
    path('path/', page_views.path_page, name='path'),
    path('path/<int:item_id>/toggle/', page_views.path_toggle, name='path_toggle'),
    path('cert/<uuid:uid>/', page_views.certificate_page, name='certificate'),
    path('sandbox/', page_views.sandbox, name='sandbox'),
    path('profile/', page_views.profile, name='profile'),
    path('favorites/toggle/', page_views.favorite_toggle, name='favorite_toggle'),
    path('blog/rss/', LatestPostsFeed(), name='blog-rss'),
    path('blog/', include('blog.urls')),
    path('projects/', include('projects.urls')),
    path('contacts/', include('contacts.urls')),
    path('talks/', include('talks.urls')),
    path('forum/', include('forum.urls')),
    path('boardapp/sso/', boards_sso, name='boards_sso'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', forum_views.register, name='register'),
    path('subscribe/', contact_views.subscribe, name='subscribe'),
    path('sitemap.xml', sitemap_view, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt',
                                            content_type='text/plain'), name='robots'),
    path('blog/rss/', LatestPostsFeed(), name='blog-rss'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
