from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from pages.notify import tg_notify

from .models import ContactRequest, Subscriber

_email_validator = EmailValidator()


def normalize_email(raw):
    """Нормализованный email либо пустая строка, если адрес некорректен."""
    email = (raw or '').strip().lower()
    try:
        _email_validator(email)
    except ValidationError:
        return ''
    return email


def contact_page(request):
    return render(request, 'contacts/contact.html')


@require_POST
def contact_submit(request):
    name = request.POST.get('name', '').strip()[:120]
    email = normalize_email(request.POST.get('email'))
    message = request.POST.get('message', '').strip()
    if not email:
        messages.error(request, 'Проверьте адрес email — он выглядит некорректно.')
        return redirect('contacts:contact')
    ContactRequest.objects.create(name=name, email=email, message=message)
    tg_notify(f'📬 Новая заявка с сайта:\n{name} ({email})\n{message[:500]}')
    messages.success(request, 'Спасибо! Я свяжусь с вами в ближайшее время.')
    return redirect('contacts:contact')


@require_POST
def subscribe(request):
    email = normalize_email(request.POST.get('email'))
    if email:
        Subscriber.objects.get_or_create(email=email)
        messages.success(request, 'Вы подписаны на обновления блога.')
    elif request.POST.get('email', '').strip():
        messages.error(request, 'Проверьте адрес email — он выглядит некорректно.')
    return redirect('/')
