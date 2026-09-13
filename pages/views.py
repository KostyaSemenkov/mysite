from django.shortcuts import render

from blog.models import Post
from projects.models import Project


def home(request):
    return render(request, 'pages/home.html', {
        'latest_posts': Post.objects.published()[:3],
        'featured_projects': Project.objects.published()[:3],
    })


def about(request):
    return render(request, 'pages/about.html')
