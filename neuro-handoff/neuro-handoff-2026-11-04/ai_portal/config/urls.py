from django.contrib import admin
from django.urls import path
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from portal import views, china_views
from portal.models import Course
class PublicationsMap(Sitemap):
    def items(self): return views.live()
class CoursesMap(Sitemap):
    def items(self): return Course.objects.filter(published=True)
urlpatterns = [path('china-ai/',china_views.index,name='china'),path('',views.home,name='home'),path('news/',views.listing,name='news'),path('articles/',views.listing,{'kind':'article'},name='articles'),path('read/<slug:slug>/',views.publication,name='publication'),path('courses/',views.courses,name='courses'),path('courses/<slug:slug>/',views.course,name='course'),path('about/',views.about,name='about'),path('admin/',admin.site.urls),path('sitemap.xml',sitemap,{'sitemaps':{'publications':PublicationsMap,'courses':CoursesMap}},name='sitemap')]
