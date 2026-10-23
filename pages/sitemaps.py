from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import Post
from forum.models import Topic
from projects.models import Project
from talks.models import Talk


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return ['home', 'about', 'blog:post_list', 'projects:project_list',
                'talks:talk_list', 'forum:topic_list', 'contacts:contact',
                'waiting_list']

    def location(self, item):
        return reverse(item)


class PostSitemap(Sitemap):
    priority = 0.9
    changefreq = 'monthly'

    def items(self):
        return Post.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class ProjectSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return Project.objects.published()

    def lastmod(self, obj):
        return obj.created_at


class TalkSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return Talk.objects.published()


class TopicSitemap(Sitemap):
    priority = 0.4
    changefreq = 'daily'

    def items(self):
        return Topic.objects.all()

    def lastmod(self, obj):
        return obj.created_at


sitemaps = {
    'static': StaticViewSitemap,
    'posts': PostSitemap,
    'projects': ProjectSitemap,
    'talks': TalkSitemap,
    'topics': TopicSitemap,
}
