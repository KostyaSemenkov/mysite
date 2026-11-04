from django.shortcuts import render
from django.core.paginator import Paginator
from .views import live, search
from .news_models import COMPANIES

def index(request):
    qs=live().filter(company__in=[v for v,_ in COMPANIES])
    company=request.GET.get('company','')
    q=request.GET.get('q','').strip()[:200]
    if company:qs=qs.filter(company=company)
    if q:qs=search(qs,q,['title','summary','body'])
    return render(request,'china.html',{'page':Paginator(qs,9).get_page(request.GET.get('page')),'companies':COMPANIES,'company':company,'q':q})
