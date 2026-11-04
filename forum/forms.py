from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import re

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


class RegisterForm(UserCreationForm):
    """Регистрация с понятными русскими подсказками и ошибками."""

    username = forms.CharField(
        label='Имя пользователя',
        max_length=150,
        help_text='3–150 символов: буквы, цифры, точка, @, +, -, _',
        error_messages={
            'required': 'Введите имя пользователя — это обязательное поле.',
            'max_length': 'Имя не может быть длиннее 150 символов.',
        },
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS, 'placeholder': 'Например: ivan_petrov'}))

    password1 = forms.CharField(
        label='Пароль',
        help_text='Минимум 8 символов, не только цифры, не только одинаковые символы',
        error_messages={'required': 'Введите пароль.'},
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))

    def _post_clean(self):
        # пропускаем Django-валидаторы пароля: наш clean_password1 уже
        # проверяет всё то же самое с понятными русскими сообщениями
        # (иначе получаем дубль: английский от Django + русский от нас)
        old = self.cleaned_data.pop('password1', None)
        old2 = self.cleaned_data.pop('password2', None)
        super()._post_clean()
        # возвращаем если валидно — иначе Django перезатрёт английскими
        if 'password1' not in self._errors:
            if old is not None:
                self.cleaned_data['password1'] = old
            if old2 is not None:
                self.cleaned_data['password2'] = old2

    password2 = forms.CharField(
        label='Повторите пароль',
        help_text='Тот же пароль ещё раз, для проверки',
        error_messages={
            'required': 'Повторите пароль.',
            'password_mismatch': 'Пароли не совпадают — перепроверьте оба поля.',
        },
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS}))

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise forms.ValidationError(
                f'Имя слишком короткое: {len(username)} симв. — нужно минимум 3.')
        if not re.match(r'^[\w.@+-]+$', username):
            bad = re.sub(r'[\w.@+-]', '', username)
            raise forms.ValidationError(
                'В имени разрешены только буквы, цифры и символы: точка ., @, +, -, _. '
                f'Уберите: {bad.strip() or "пробелы"}')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                f'Имя «{username}» уже занято. Попробуйте добавить цифру или дефис.')
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        if len(password) < 8:
            raise forms.ValidationError(
                f'Пароль слишком короткий: {len(password)} симв. — нужно минимум 8.')
        if password.isdigit():
            raise forms.ValidationError(
                'Пароль не может состоять только из цифр — добавьте буквы или символы.')
        if len(set(password)) == 1:
            raise forms.ValidationError(
                'Пароль не может состоять из одного повторяющегося символа.')
        username = self.data.get('username', '')
        if username and username.lower() in password.lower():
            raise forms.ValidationError(
                'Пароль не должен содержать ваше имя пользователя.')
        return password

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(
                'Пароли не совпадают — перепроверьте оба поля.')
        return p2


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
        if self._user is not None and self._user.is_authenticated \
                and rate_limited(self._user, 'comment'):
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
            pass
        elif self._user is not None and rate_limited(self._user, 'topic'):
            raise forms.ValidationError('Слишком много тем за час — попробуйте позже.')
        return cleaned
