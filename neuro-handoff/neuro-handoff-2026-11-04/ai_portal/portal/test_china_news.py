from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, Client
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from portal.models import Publication
from portal.news_models import NewsSource, IncomingNews
from portal.news.adapters import Entry, kimi, zai, deepseek, qwen, clean, relevant
from portal.news.fetch import validate_url
from portal.news.service import collect, mark_ready, publish, revision

class FakeFetch:
    def __init__(self, pages): self.pages=pages
    def get(self,url): return self.pages[url]

class AdaptersTests(SimpleTestCase):
    def test_kimi_card_owns_its_link(self):
        html='<main><div class="menu-card"><h4>Kimi K3</h4><p class="card-date">2026-07-16</p><a href="/en/blog/kimi-k3"></a></div><div class="menu-card"><h4>Kimi K1.5</h4><p class="card-date">2025-01-20</p><a href="https://github.com/MoonshotAI/Kimi-k1.5"></a></div></main>'
        rows=kimi(FakeFetch({'https://www.kimi.com/en/blog/':html,'https://platform.kimi.ai/blog':'','https://platform.kimi.ai/blog/posts/changelog':''}))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0].title,'Kimi K3')
    def test_zai_date_blocks(self):
        html='<div id="content"><div class="update" id="2026-08-26"><button>2026-08-26</button><h3>GLM-5.3-Flash</h3><p>New model.</p></div></div>'
        rows=zai(FakeFetch({'https://docs.z.ai/release-notes/new-released':html}))
        self.assertEqual(rows[0].title,'GLM-5.3-Flash');self.assertTrue(rows[0].url.endswith('#2026-08-26'))
    def test_deepseek_one_entry_per_date(self):
        html='<article><h2 id="date-2026-09-10">Date: 2026-09-10</h2><h3>DeepSeek new model</h3><p>New API.</p><h2 id="date-2026-08-21">Date: 2026-08-21</h2><h3>Previous release</h3><p>Old API.</p></article>'
        rows=deepseek(FakeFetch({'https://api-docs.deepseek.com/updates/':html}))
        self.assertEqual(len(rows),2);self.assertNotIn('Old API',rows[0].text)
    def test_qwen_public_json_and_exclusions(self):
        import json
        data={'success':True,'data':{'articles':[{'path':'qwen-new','title':'Qwen New Model','extra':{'date':'2026-09-18T17:30:00+08:00'},'content':'<article>'+('Useful content. '*20)+'</article>'},{'path':'jobs','title':'Qwen hiring','extra':{},'content':''}]}}
        rows=qwen(FakeFetch({'https://qwen.ai/api/v2/article/retrieval?type=qwen_ai&language=en-US':json.dumps(data)}))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0].date.utcoffset(),timedelta(hours=8))
    def test_filter_and_html_safety(self):
        for title in ['Kimi hiring globally','Qwen coupon giveaway','PerceptionBench','Qwen Tutorial']:
            self.assertFalse(relevant(title))
        self.assertTrue(relevant('Kimi API pricing update'))
        self.assertNotIn('alert',clean('<p>News</p><script>alert(1)</script>'))
    def test_only_official_https(self):
        for url in ['http://qwen.ai/','https://qwen.ai.evil.test/','https://127.0.0.1/','https://user:pass@qwen.ai/','https://qwen.ai:8080/']:
            with self.assertRaises(ValueError):validate_url(url)

class WorkflowTests(TestCase):
    def setUp(self):
        self.source=NewsSource.objects.create(company='qwen')
        self.user=get_user_model().objects.create_superuser('reviewer','reviewer@example.test','test-password-123')
        self.rows=[Entry(str(i),f'https://qwen.ai/blog?id=test-{i}',f'Qwen Model {i}',timezone.now()-timedelta(days=i),'Official text with useful details. '*15) for i in range(8)]
    def gather(self,rows=None):
        with patch('portal.news.service.discover',return_value=self.rows if rows is None else rows):
            return collect(self.source,4,FakeFetch({}))
    def test_initial_cap_idempotence_new_only(self):
        self.gather();self.assertEqual(IncomingNews.objects.count(),4)
        run=self.gather();self.assertEqual(run.created,0);self.assertEqual(IncomingNews.objects.count(),4)
        new=Entry('new','https://qwen.ai/blog?id=new','Qwen New Model',timezone.now(),'New full text. '*20)
        self.gather([new]+self.rows);self.assertEqual(IncomingNews.objects.count(),5)
        self.assertEqual(Publication.objects.count(),0)
    def prepare(self):
        self.gather();item=IncomingNews.objects.first()
        item.title_ru='Новая модель Qwen';item.summary_ru='Короткое описание официального обновления.';item.body_ru='Компания представила новую модель. Подробности приведены в официальном источнике.';item.save();mark_ready(item);item.refresh_from_db();return item
    def test_manual_approval_and_source_changes(self):
        item=self.prepare();pub=publish(item,self.user)
        self.assertContains(self.client.get('/china-ai/'),item.title_ru)
        self.rows[0].text+='An important correction.'
        self.gather();item.refresh_from_db();pub.refresh_from_db()
        self.assertEqual(item.status,'changed');self.assertEqual(pub.body,item.body_ru)
        with self.assertRaises(ValidationError):publish(item,self.user)
        self.assertEqual(Publication.objects.count(),1)
        mark_ready(item);publish(item,self.user);self.assertEqual(Publication.objects.count(),1)
    def test_incomplete_and_stale_cannot_publish(self):
        self.gather();item=IncomingNews.objects.first()
        with self.assertRaises(ValidationError):publish(item,self.user)
        item=self.prepare();item.summary_source_hash='outdated';item.save()
        with self.assertRaises(ValidationError):publish(item,self.user)
    def test_errors_visible_and_retry(self):
        with patch('portal.news.service.discover',side_effect=ValueError('Source format changed')):run=collect(self.source,fetch=FakeFetch({}))
        self.assertIn('Source format changed',run.error)
        self.assertFalse(self.source.initialized)
        self.gather();self.source.refresh_from_db();self.assertEqual(self.source.last_error,'')
        self.assertIsNotNone(self.source.last_success)
    def test_private_queue_preview_permissions_and_escape(self):
        item=self.prepare();url=f'/admin/portal/incomingnews/{item.pk}/preview/'
        self.assertEqual(self.client.get(url).status_code,302)
        self.assertNotContains(self.client.get('/china-ai/'),item.title_ru)
        self.assertNotContains(self.client.get('/sitemap.xml'),item.title_ru)
        self.client.force_login(self.user);self.assertContains(self.client.get(url),item.title_ru)
        staff=get_user_model().objects.create_user('staff',is_staff=True)
        self.client.force_login(staff);self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.user)
        item.original_text='<script>alert(1)</script>';item.save()
        self.assertNotContains(self.client.get(url),'<script>alert(1)</script>')
    def test_rejected_items_stay_rejected(self):
        self.gather();item=IncomingNews.objects.first();item.status='rejected';item.save()
        self.rows[0].text+='Correction';self.gather();item.refresh_from_db();self.assertEqual(item.status,'rejected')
    def test_company_filter_and_source_date(self):
        item=self.prepare();pub=publish(item,self.user)
        self.assertNotContains(self.client.get('/china-ai/?company=kimi'),item.title_ru)
        self.assertContains(self.client.get('/china-ai/?company=qwen'),item.title_ru)
        self.assertEqual(pub.published_at,item.source_date)

    def test_preview_approval_requires_fresh_post_and_is_not_repeated(self):
        item=self.prepare();url=f'/admin/portal/incomingnews/{item.pk}/preview/'
        self.client.force_login(self.user)
        response=self.client.get(url+'?action=publish')
        self.assertEqual(Publication.objects.count(),0)
        token=response.context['revision']
        self.assertContains(response,'Одобрить и опубликовать')
        self.assertContains(self.client.post(url,{'action':'publish'},follow=True),'Новость изменилась')
        self.assertEqual(Publication.objects.count(),0)
        self.client.post(url,{'action':'publish','revision':token})
        item.refresh_from_db()
        self.assertEqual(item.status,'published');self.assertEqual(item.approved_by,self.user)
        self.assertEqual(Publication.objects.count(),1)
        self.assertContains(self.client.post(url,{'action':'publish','revision':token},follow=True),'Новость изменилась')
        self.assertEqual(Publication.objects.count(),1)

    def test_preview_stale_source_and_editor_revision_block_actions(self):
        item=self.prepare();url=f'/admin/portal/incomingnews/{item.pk}/preview/'
        self.client.force_login(self.user);token=revision(item)
        self.rows[0].text+='Corrected official details.';self.gather()
        for action in ['publish','ready','reject']:
            self.assertContains(self.client.post(url,{'action':action,'revision':token},follow=True),'Новость изменилась')
        item.refresh_from_db();self.assertEqual(item.status,'changed')
        self.assertEqual(Publication.objects.count(),0)
        mark_ready(item);item.refresh_from_db();token=revision(item)
        item.body_ru+=' Редактор уточнил изложение.';item.save()
        with self.assertRaises(ValidationError):publish(item,self.user,token)

    def test_preview_action_permissions_and_csrf(self):
        item=self.prepare();url=f'/admin/portal/incomingnews/{item.pk}/preview/'
        staff=get_user_model().objects.create_user('reader',is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename='view_incomingnews'))
        self.client.force_login(staff)
        self.assertNotContains(self.client.get(url),'Одобрить и опубликовать')
        self.assertEqual(self.client.post(url,{'action':'ready','revision':revision(item)}).status_code,403)
        staff.user_permissions.add(Permission.objects.get(codename='change_incomingnews'))
        self.assertEqual(self.client.post(url,{'action':'publish','revision':revision(item)}).status_code,403)
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.user)
        self.assertEqual(secure.post(url,{'action':'publish','revision':revision(item)}).status_code,403)
        secure.get(url)
        response=secure.post(url,{'action':'publish','revision':revision(item),'csrfmiddlewaretoken':secure.cookies['csrftoken'].value})
        self.assertEqual(response.status_code,302);self.assertEqual(Publication.objects.count(),1)

    def test_edit_form_rejects_stale_data_then_saves_current_revision(self):
        item=self.prepare();url=f'/admin/portal/incomingnews/{item.pk}/change/'
        self.client.force_login(self.user)
        form=self.client.get(url).context['adminform'].form
        payload={'revision':form.initial['revision'],'title_ru':item.title_ru,'summary_ru':item.summary_ru,'body_ru':item.body_ru+' Правка редактора.','event':item.event,'editor_note':'','_save':'Save'}
        self.rows[0].text+='Official correction.';self.gather()
        self.assertContains(self.client.post(url,payload),'Новость изменилась')
        item.refresh_from_db();self.assertNotIn('Правка редактора',item.body_ru)
        self.assertIn('Official correction',item.original_text)
        payload['revision']=revision(item)
        self.assertEqual(self.client.post(url,payload).status_code,302)
        item.refresh_from_db();self.assertEqual(item.status,'waiting')
        self.assertIn('Правка редактора',item.body_ru);self.assertEqual(item.summary_source_hash,'')
        preview=f'/admin/portal/incomingnews/{item.pk}/preview/'
        self.client.post(preview,{'action':'ready','revision':revision(item)})
        item.refresh_from_db();self.assertEqual(item.status,'review')
        self.client.post(preview,{'action':'reject','revision':revision(item)})
        item.refresh_from_db();self.assertEqual(item.status,'rejected')

    def test_collection_does_not_reenable_source_disabled_during_fetch(self):
        def discover_while_disabling(*args):
            NewsSource.objects.filter(pk=self.source.pk).update(enabled=False)
            return self.rows
        with patch('portal.news.service.discover',side_effect=discover_while_disabling):
            collect(self.source,fetch=FakeFetch({}))
        self.source.refresh_from_db();self.assertFalse(self.source.enabled)
