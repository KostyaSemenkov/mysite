from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import ContactRequest, Subscriber


def contact_page(request):
    return render(request, 'contacts/contact.html')


@require_POST
def contact_submit(request):
    ContactRequest.objects.create(
        name=request.POST.get('name', '').strip()[:120],
        email=request.POST.get('email', '').strip(),
        message=request.POST.get('message', '').strip(),
    )
    messages.success(request, 'Спасибо! Я свяжусь с вами в ближайшее время.')
    return redirect('contacts:contact')


@require_POST
def subscribe(request):
    email = request.POST.get('email', '').strip().lower()
    if email:
        Subscriber.objects.get_or_create(email=email)
        messages.success(request, 'Вы подписаны на обновления блога.')
    return redirect('/')
