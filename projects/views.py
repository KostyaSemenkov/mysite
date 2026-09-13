from django.shortcuts import get_object_or_404, render

from .models import Project


def project_list(request):
    return render(request, 'projects/project_list.html',
                  {'projects': Project.objects.published()})


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug, is_published=True)
    return render(request, 'projects/project_detail.html', {'project': project})
