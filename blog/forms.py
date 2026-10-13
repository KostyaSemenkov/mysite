from django import forms

from .models import GuestPostSubmission

INPUT_CLASS = ('w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2.5 '
               'focus:border-indigo-500 focus:outline-none')


class GuestPostForm(forms.ModelForm):
    class Meta:
        model = GuestPostSubmission
        fields = ('title', 'excerpt', 'content', 'tags')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'О чём пост?', 'class': INPUT_CLASS}),
            'excerpt': forms.TextInput(attrs={'placeholder': 'Краткое описание (необязательно)',
                                              'class': INPUT_CLASS}),
            'content': forms.Textarea(attrs={'rows': 10, 'placeholder': 'Текст поста',
                                             'class': INPUT_CLASS}),
            'tags': forms.TextInput(attrs={'placeholder': 'Теги через запятую', 'class': INPUT_CLASS}),
        }
