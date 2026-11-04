from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Publication, Course

def search(qs, query, fields):
    # Python casefold supports Russian on SQLite as well as other databases.
    needle=query.casefold()
    ids=[row['pk'] for row in qs.values('pk',*fields) if any(needle in str(row[field]).casefold() for field in fields)]
    return qs.filter(pk__in=ids)

def live(): return Publication.objects.filter(published=True,published_at__lte=timezone.now())
def home(request):
    news=live().filter(kind='news')
    hero=news.filter(featured=True).first() or news.first()
    return render(request,'home.html',{'hero':hero,'news':news.exclude(pk=hero.pk)[:6] if hero else news,'articles':live().filter(kind='article')[:3],'courses':Course.objects.filter(published=True)[:4]})
def listing(request,kind='news'):
    qs=live().filter(kind=kind)
    q=request.GET.get('q','').strip()
    topic=request.GET.get('topic','')
    if q: qs=search(qs,q,['title','summary','body'])
    if topic: qs=qs.filter(topic=topic)
    return render(request,'listing.html',{'page':Paginator(qs,9).get_page(request.GET.get('page')),'title':'Новости' if kind=='news' else 'Статьи и инструкции','kind':kind,'topics':Publication.TOPICS,'q':q,'topic':topic})
def publication(request,slug):
    item=get_object_or_404(live(),slug=slug)
    return render(request,'publication.html',{'item':item,'related':live().filter(topic=item.topic).exclude(pk=item.pk)[:3]})
def courses(request):
    qs=Course.objects.filter(published=True)
    q=request.GET.get('q','').strip()
    if q: qs=search(qs,q,['title','summary'])
    for field in ['level','direction']:
        if request.GET.get(field): qs=qs.filter(**{field:request.GET[field]})
    if request.GET.get('price')=='free': qs=qs.filter(price=0)
    if request.GET.get('price')=='paid': qs=qs.filter(price__gt=0)
    return render(request,'courses.html',{'page':Paginator(qs,9).get_page(request.GET.get('page')),'has_demo':qs.filter(demo=True).exists(),'levels':Course.LEVELS,'topics':Publication.TOPICS,'q':q})
def course(request,slug):
    item=get_object_or_404(Course,published=True,slug=slug)
    return render(request,'course.html',{'item':item,'modules':item.program.splitlines()})
def about(request): return render(request,'about.html')
