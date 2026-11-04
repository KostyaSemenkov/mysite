from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Publication,Course
class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command('seed_demo',verbosity=0)
        cls.draft=Publication.objects.create(title='Secret draft',slug='draft',topic='tools',summary='draft',body='hidden')
        cls.future=Publication.objects.create(title='Future',slug='future',topic='tools',summary='future',body='hidden',published=True,published_at=timezone.now()+timedelta(days=1))
    def test_public_pages(self):
        for path in ['/','/news/','/articles/','/courses/','/about/','/sitemap.xml','/admin/login/']:
            self.assertEqual(self.client.get(path).status_code,200,path)
        for obj in list(Publication.objects.filter(demo=True))+list(Course.objects.all()):
            self.assertEqual(self.client.get(obj.get_absolute_url()).status_code,200)
    def test_unpublished_hidden(self):
        for slug in ['draft','future','missing']:
            self.assertEqual(self.client.get(reverse('publication',args=[slug])).status_code,404)
        self.assertNotContains(self.client.get('/sitemap.xml'),'/read/draft/')
        c=Course.objects.first();c.published=False;c.save()
        self.assertEqual(self.client.get(c.get_absolute_url()).status_code,404)
    def test_filters_and_pagination(self):
        self.assertContains(self.client.get('/news/',{'q':'НЕЙРОСЕТЬ'}),'Нейросеть на своём компьютере')
        response=self.client.get('/news/',{'q':'Python'})
        self.assertEqual(response.context['page'].paginator.count,1)
        response=self.client.get('/news/',{'topic':'creative'})
        self.assertTrue(all(x.topic=='creative' for x in response.context['page']))
        self.assertEqual(len(self.client.get('/news/').context['page']),9)
        self.assertEqual(len(self.client.get('/news/',{'page':2}).context['page']),3)
        response=self.client.get('/courses/',{'price':'free','level':'beginner'})
        self.assertEqual(response.context['page'].paginator.count,2)
        self.assertTrue(all(x.price==0 for x in response.context['page']))
        self.assertContains(self.client.get('/news/',{'q':'doesnotexist'}),'Пока ничего не нашлось')
    def test_demo_enrollment_disabled(self):
        c=Course.objects.first();c.external_url='https://example.com/enroll';c.save()
        self.assertNotContains(self.client.get(c.get_absolute_url()),'href="https://example.com/enroll"')
    def test_admin_requires_login(self):
        self.assertEqual(self.client.get('/admin/portal/publication/').status_code,302)
