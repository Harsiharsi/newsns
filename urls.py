from django.urls import path
from . import views

app_name = 'newsns'

urlpatterns = [
    path('', views.index, name='index'),
    path('post', views.post, name='post'),
    path('confirm', views.confirm, name='confirm'),
    path('article/', views.redirect_to_index, name='redirect_to_index'),
    path('article/<int:id>', views.article, name='article'),
    path('censored_word_list', views.censored_word_list, name='censored_word_list'),
    path('secret_word_list/<censored_word>', views.secret_word_list, name='secret_word_list'),
    path('post_comment/', views.redirect_to_index, name='redirect_to_index'),
    path('post_comment/<int:id>', views.post_comment, name='post_comment'),
    path('confirm_comment/', views.confirm_comment, name='confirm_comment'),
    path('signup', views.signup, name='signup'),
    path('login', views.login_view, name='login_view'),
    path('logout', views.logout_view, name='logout_view'),
    path('search_articles', views.search_articles, name='search_articles'),
    path('result', views.result, name='result'),
]
