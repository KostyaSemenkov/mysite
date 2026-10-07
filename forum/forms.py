from django import forms

from .models import Comment, Topic

INPUT_CLASS = ('w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2.5 '
               'focus:border-indigo-500 focus:outline-none')


class CommentForm(forms.ModelForm):
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
        if user is not None and user.is_authenticated:
            self.fields['guest_name'].widget = forms.HiddenInput()
        else:
            self.fields['guest_name'].required = True

    def clean_guest_name(self):
        return self.cleaned_data.get('guest_name', '').strip()[:120]


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ('title', 'body')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'О чём тема?', 'class': INPUT_CLASS}),
            'body': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Первое сообщение',
                                          'class': INPUT_CLASS}),
        }
