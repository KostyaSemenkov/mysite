from django import forms
from django.utils import timezone
from datetime import timedelta

from .models import Comment, Topic

INPUT_CLASS = ('w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2.5 '
               'focus:border-indigo-500 focus:outline-none')

HONEYPOT_HELP = 'Оставьте поле пустым'

RATE_LIMITS = {
    'topic': (5, timedelta(hours=1)),      # 5 тем в час
    'comment': (15, timedelta(hours=1)),   # 15 комментариев в час
}


class HoneypotMixin:
    """Скрытое поле-ловушка: боты заполняют все поля, люди его не видят."""

    def add_honeypot(self):
        self.fields['website'] = forms.CharField(
            required=False, label='Сайт',
            widget=forms.TextInput(attrs={
                'class': 'hp-field', 'tabindex': '-1',
                'autocomplete': 'off', 'aria-hidden': 'true'}),
            help_text=HONEYPOT_HELP)

    def honeypot_triggered(self) -> bool:
        return bool(self.cleaned_data.get('website'))


def rate_limited(user, kind: str) -> bool:
    """Не больше N объектов за период для залогиненного пользователя."""
    limit, period = RATE_LIMITS[kind]
    since = timezone.now() - period
    if kind == 'topic':
        count = Topic.objects.filter(created_by=user, created_at__gte=since).count()
    else:
        count = Comment.objects.filter(author=user, created_at__gte=since).count()
    return count >= limit


class CommentForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('guest_name', 'body')
        widgets = {
            'guest_name': forms.TextInput(attrs={'placeholder': 'Ваше имя', 'class': INPUT_CLASS}),
            'body': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Ваш комментарий',
                                          'class': INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.add_honeypot()
        if user is not None and user.is_authenticated:
            self.fields['guest_name'].widget = forms.HiddenInput()
        else:
            self.fields['guest_name'].required = True

    def clean(self):
        cleaned = super().clean()
        if self.honeypot_triggered():
            raise forms.ValidationError('')
        if self._user is not None and self._user.is_authenticated                 and rate_limited(self._user, 'comment'):
            raise forms.ValidationError('Слишком много комментариев за час — чуть позже.')
        return cleaned

    def clean_guest_name(self):
        return self.cleaned_data.get('guest_name', '').strip()[:120]


class TopicForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = Topic
        fields = ('title', 'body')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'О чём тема?', 'class': INPUT_CLASS}),
            'body': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Первое сообщение',
                                          'class': INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.add_honeypot()

    def clean(self):
        cleaned = super().clean()
        if self.honeypot_triggered():
            # боту отвечаем «успехом» во вьюхе, но ничего не создаём
            pass
        elif self._user is not None and rate_limited(self._user, 'topic'):
            raise forms.ValidationError('Слишком много тем за час — попробуйте позже.')
        return cleaned
