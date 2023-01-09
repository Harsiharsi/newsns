from django.db import models
from django.contrib.auth.models import User

class Article(models.Model):
    contributor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='a_contributor')
    content = models.TextField()
    posted_date = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    contributor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='c_contributor')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='c_article')
    content = models.TextField()
    is_article_contributor = models.BooleanField(default=False)
    posted_date = models.DateTimeField(auto_now_add=True)
    first_posted_date = models.DateTimeField(auto_now_add=True)

class CensoredWord(models.Model):
    censored_word = models.TextField()
    secret_word = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['censored_word', 'secret_word'],
                name='censored_word_unique'
            )
        ]

    @classmethod
    def is_registerable(cls, sw):
        if CensoredWord.objects.filter(censored_word__icontains=sw):
            return False
        return True

class CensoredWordHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user')
    censored_word = models.ForeignKey(CensoredWord, on_delete=models.CASCADE, related_name='cwh_censored_word')
    date = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'censored_word'],
                name='censored_word_history_unique'
            )
        ]
