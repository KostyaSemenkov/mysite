from django.shortcuts import get_object_or_404, render

from .models import Talk


def talk_list(request):
    return render(request, 'talks/talk_list.html', {'talks': Talk.objects.published()})


def talk_detail(request, slug):
    talk = get_object_or_404(Talk, slug=slug, is_published=True)
    return render(request, 'talks/talk_detail.html', {'talk': talk})
