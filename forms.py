from django import forms
from .models import Article
from django.contrib.auth.models import User

class LoginForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), label='password')

    class Meta:
        model = User
        fields = ['email', 'password']

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['content']
        labels = {'content':''}

class SearchForm(forms.Form):
    keywords = forms.CharField(label='keywords')

class RegisterCensoredWordForm(forms.Form):
    censored_word = forms.CharField(label='register_censored_word')
    secret_word = forms.CharField(label='register_secret_word')

class CensoredWordSelectForm(forms.Form):
    pass
