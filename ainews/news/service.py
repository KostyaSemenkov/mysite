import hashlib
import json
import re
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from ainews.models import Publication
from ainews.models import IncomingNews, ImportRun
from .adapters import discover, article_text
from .fetch import Fetcher

def fingerprint(entry):
    return hashlib.sha256((entry.title+'\n'+entry.date.isoformat()+'\n'+re.sub(r'\s+',' ',entry.text)).encode()).hexdigest()

def collect(source, initial_limit=4, fetch=None):
    run=ImportRun.objects.create(source=source)
    source.last_checked=timezone.now();source.save(update_fields=['last_checked'])
    fetch=fetch or Fetcher()
    try:
        entries=discover(source.company,fetch)
        known=set(source.seen_keys)
        existing={n.source_key:n for n in IncomingNews.objects.filter(source=source)}
        # Initial import is bounded; subsequent runs do not flood the queue with the archive.
        selected=entries[:initial_limit] if not source.initialized else [e for e in entries if e.key in existing or e.key not in known]
        errors=[]
        for e in selected:
            try:
                if not e.text: e.text=article_text(fetch.get(e.url))
                if len(e.text)<100: raise ValueError('Слишком короткий текст источника')
                digest=fingerprint(e)
                with transaction.atomic():
                    item,created=IncomingNews.objects.select_for_update().get_or_create(source=source,source_key=e.key,defaults={'source_url':e.url,'original_title':e.title,'original_text':e.text,'source_date':e.date,'content_hash':digest,'event':e.event})
                    if created: run.created+=1
                    elif item.content_hash!=digest:
                        item.previous_text=item.original_text
                        item.original_title=e.title;item.original_text=e.text;item.source_date=e.date;item.source_url=e.url;item.content_hash=digest
                        if item.status!='rejected': item.status='changed'
                        item.save(update_fields=['previous_text','original_title','original_text','source_date','source_url','content_hash','status','updated_at']);run.changed+=1
                    else: run.skipped+=1
                known.add(e.key)
            except Exception as exc:
                errors.append(f'{e.title[:100]}: {type(exc).__name__}: {str(exc)[:200]}')
        if not source.initialized:
            # Remember the unselected archive, but retry failed selected items next run.
            selected_keys={e.key for e in selected}
            known.update(e.key for e in entries if e.key not in selected_keys)
            source.initialized=True
        source.seen_keys=sorted(known)
        if errors: raise ValueError('; '.join(errors)[:2000])
        source.last_success=timezone.now();source.last_error=''
    except Exception as exc:
        source.last_error=f'{type(exc).__name__}: {str(exc)[:2000]}'
        run.error=source.last_error
    finally:
        source.save(update_fields=['initialized','seen_keys','last_success','last_error'])
        run.finished_at=timezone.now();run.save()
    return run

def validate_summary(item):
    for value in [item.title_ru,item.summary_ru,item.body_ru]:
        if not value.strip() or not re.search('[а-яА-ЯёЁ]',value):
            raise ValidationError('Заполните заголовок, описание и изложение на русском языке.')
    if len(item.title_ru)>220 or len(item.summary_ru)>400:
        raise ValidationError('Заголовок — до 220 символов, описание — до 400.')

def revision(item):
    """Identify the exact source and editorial state shown to the reviewer."""
    values=[item.content_hash,item.summary_source_hash,item.title_ru,item.summary_ru,
            item.body_ru,item.event,item.editor_note,item.status,item.publication_id,
            item.updated_at.isoformat()]
    return hashlib.sha256(json.dumps(values,ensure_ascii=False).encode()).hexdigest()

def check_revision(item,expected):
    if expected is not None and revision(item)!=expected:
        raise ValidationError('Новость изменилась после открытия страницы. Обновите страницу и проверьте актуальную версию; действие не выполнено.')

@transaction.atomic
def mark_ready(item,expected_revision=None):
    item=IncomingNews.objects.select_for_update().get(pk=item.pk)
    check_revision(item,expected_revision)
    validate_summary(item)
    item.summary_source_hash=item.content_hash
    item.status='review'
    item.save()

@transaction.atomic
def publish(item,user,expected_revision=None):
    item=IncomingNews.objects.select_for_update().get(pk=item.pk)
    check_revision(item,expected_revision)
    validate_summary(item)
    if item.status!='review' or item.summary_source_hash!=item.content_hash:
        raise ValidationError('Сначала проверьте актуальный оригинал и отметьте русский текст готовым к проверке.')
    values={'title':item.title_ru,'summary':item.summary_ru,'body':item.body_ru,'kind':'news','topic':'tools','company':item.source.company,'author':'Редакция НЕЙРО · по официальному источнику','published':True,'demo':False,'published_at':item.source_date,'source_url':item.source_url}
    if item.publication_id:
        Publication.objects.filter(pk=item.publication_id).update(**values)
    else:
        item.publication=Publication.objects.create(slug=f'china-{item.source.company}-{item.pk}',**values)
    item.status='published';item.approved_by=user;item.approved_at=timezone.now();item.save()
    return item.publication

@transaction.atomic
def reject(item,expected_revision=None):
    item=IncomingNews.objects.select_for_update().get(pk=item.pk)
    check_revision(item,expected_revision)
    item.status='rejected'
    item.save(update_fields=['status','updated_at'])
