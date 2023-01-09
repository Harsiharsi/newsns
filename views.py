from django import forms
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from .models import Article, Comment, CensoredWord, CensoredWordHistory
from .forms import ArticleForm, LoginForm, SearchForm, RegisterCensoredWordForm, CensoredWordSelectForm

import re


def signup(request):
    params = {
        'form':LoginForm,
    }

    if request.method == 'POST':
        form = LoginForm(data=request.POST)

        if form.is_valid():
            account = User()
            account.username = request.POST['email']
            account.email = request.POST['email']
            account.set_password(request.POST['password'])
            account.save()
            return redirect(to='newsns/index.html')
        else:
            messages.error(request, '入力が有効ではありません')
            return redirect(to='newsns/signup.html')

    return render(request, 'newsns/signup.html', params)

def login_view(request):
    params = {
        'form':LoginForm(),
    }

    if request.method == 'POST':
        user = authenticate(
            email=request.POST.get('email'),
            password=request.POST.get('password'))
        if user:
            if user.is_active:
                login(request, user)
                return redirect(to='/newsns')
            else:
                messages.error(request, 'アカウントが有効ではありません')
                return redirect(to='/newsns')
        else:
            messages.error(request, 'eメールアドレスまたはパスワードが間違っています')
            return redirect(to='/newsns')
    else:
        return render(request, 'newsns/login.html', params)

@login_required(login_url='/newsns/login')
def logout_view(request):
    logout(request)
    return redirect(to='/newsns/')

@login_required(login_url='/newsns/login')
def index(request):
    params = {
        'login_user':request.user,
        'message':messages,
        'articles':Article.objects.all()
    }

    return render(request, 'newsns/index.html', params)

def search_articles(request):
    params = {
        'form':SearchForm(),
        'search_string':None,
        'result':None,
    }

    if request.method == 'POST':
        params['search_string'] = request.POST.get('keywords')

        def f(p):
            q = Q()
            conjunction = Q.AND
            for w in p:
                if w[0] == '-':
                    denial = True
                else:
                    denial = False

                if isinstance(w, list):
                    q.add(f(w), conjunction)
                elif w == 'OR':
                    conjunction = Q.OR
                    continue
                elif denial:
                    q.add(~Q(content__icontains=w[1:]), conjunction)
                else:
                    q.add(Q(content__icontains=w), conjunction)
                conjunction = Q.AND
            return q

        params['result'] = Article.objects.filter(f(parser(request.POST.get('keywords'))))

        return render(request, 'newsns/result.html', params)

    return render(request, 'newsns/search.html', params)

def result(request):
    params = {
        'form':SearchForm(),
        'result':None,
    }

    if request.method == 'POST':
        params['result'] = request.POST['result']
        return render(request, 'newsns/result.html', params)

    return redirect(to='/newsns')

@login_required(login_url='/newsns/login')
def post(request):
    params = {
        'login_user':request.user,
        'form':ArticleForm,
        'content':None,
    }

    if request.method == 'POST':
        params_for_confirm = {
            'content':request.POST.get('content'),
            'forms':None,
        }

        if validate_brackets(request.POST.get('content')) == 0:
            censored_word_list = []
            for cw in CensoredWord.objects.all().order_by('censored_word').distinct().values_list('censored_word'):
                if cw[0] in request.POST.get('content'):
                    censored_word_list.append(cw[0])

            if censored_word_list:
                select_forms = CensoredWordSelectForm()
                for cw in censored_word_list:
                    data = [(cw, 'not replace')] + \
                    [(sw.secret_word, sw.secret_word) for sw in CensoredWord.objects.filter(censored_word=cw)]
                    select_forms.fields[cw] = forms.ChoiceField(choices=data, label=cw)
                params_for_confirm['forms'] = select_forms
                return render(request, 'newsns/confirm.html', params_for_confirm)
        else:
            messages.error(request, 'カッコの対応が正しくありません')
            params['content'] = request.POST.get('content')
            return render(request, 'newsns/post.html', params)

        a = Article()
        a.contributor = request.user
        a.content = number_brackets(request.POST.get('content'))
        a.save()
        messages.success(request, '文章を投稿しました')
        return redirect(to='/newsns')
    
    return render(request, 'newsns/post.html', params)

@login_required(login_url='/newsns/login')
def confirm(request):
    if request.method == 'POST':
        if request.POST.get('notpost'):
            params = {
                'login_user':request.user,
                'form':ArticleForm,
                'content':request.POST.get('content'),
            }
            return render(request, 'newsns/post.html', params)
            
        content = request.POST.get('content')
        is_censored_word_contained = True
        is_replaced = False
        while is_censored_word_contained:
            is_censored_word_contained = False
            for cw in CensoredWord.objects.all().distinct().values_list('censored_word').reverse():
                if cw[0] in content:
                    if 'not replace' in request.POST or cw[0] in request.POST:
                        content = content.replace(cw[0], request.POST.get(cw[0]))
                        if CensoredWordHistory.objects.filter(
                            user=request.user,
                            censored_word=CensoredWord.objects.filter(
                                censored_word=cw[0],
                                secret_word=request.POST.get(cw[0])).first()):
                            CensoredWordHistory.objects.filter(
                                user=request.user,
                                censored_word=CensoredWord.objects.filter(
                                    censored_word=cw[0],
                                    secret_word=request.POST.get(cw[0])).first()).first().save()
                        is_censored_word_contained = True
                        continue
                    else:
                        if CensoredWordHistory.objects.filter(
                            user=request.user,
                            censored_word=CensoredWord.objects.filter(
                                censored_word=cw[0],
                                secret_word=request.POST.get(cw[0])).first()):
                            s = CensoredWordHistory.objects.filter(
                                    user=request.user,
                                    censored_word=CensoredWord.objects.filter(
                                        censored_word=cw[0],
                                        secret_word=request.POST.get(cw[0])).first()).first().censored_word.secretword
                        else:
                            s = CensoredWord.objects.filter(censored_word=cw[0]).order_by('?').first().secret_word
                        content = content.replace(cw[0], s)
                    is_censored_word_contained = True
        a = Article()
        a.contributor = request.user
        a.content = number_brackets(content)
        a.save()
        messages.success(request, '文章を投稿しました')
        return redirect(to='/newsns')

    return redirect(to='/newsns')

#@login_required(login_url='/newsns/login')
#def post_comment(request, id):
#    if request.method == 'POST':
#        c = Comment()
#        c.contributor = request.user
#        c.article = Article.objects.get(id=id)
#        c.content = request.POST['content']
#        c.save()
#
#        first_posted_comment = Comment.objects.filter(
#                                Q(contributor=c.contributor) &
#                                Q(article=c.article)).order_by('posted_date').first()
#        if first_posted_comment:
#            c.first_posted_date = first_posted_comment.posted_date
#            c.save()
#
#        messages.success(request, 'コメントを投稿しました')
#        return redirect(to='/newsns')
#    else:
#        if Article.objects.filter(id=id):
#            a = Article.objects.get(id=id)
#            f = ArticleForm
#        else:
#            a = None
#            f = None
#            messages.error(request, 'この記事は存在しません')
#        
#    params = {
#        'login_user':request.user,
#        'article':a,
#        'article_id':id,
#        'form':f,
#    }
#
#    return render(request, 'newsns/post_comment.html', params)

#@login_required(login_url='/newsns/login')
#def post_comment(request, id):
#    params = {
#        'login_user':request.user,
#        'form':ArticleForm,
#        'article':None,
#    }
#
#    if Article.objects.filter(id=id):
#        params['artcile'] = Article.objects.get(id=id)
#    else:
#        messages.error(request, 'この記事は存在しません')
#    
#    return render(request, 'newsns/post_comment.html', params)

@login_required(login_url='/newsns/login')
def post_comment(request, id):
    params = {
        'login_user':request.user,
        'form':ArticleForm(),
        'content':None,
        'article':None,
    }

    if Article.objects.filter(id=id):
        params['article'] = Article.objects.get(id=id)
    else:
        messages.error(request, 'この記事は存在しません')
        return render(request, 'newsns/post_comment.html', params)

    if request.method == 'POST':
        params_for_confirm = {
            'content':request.POST.get('content'),
            'forms':None,
            'article':Article.objects.get(id=id),
        }

        if validate_brackets(request.POST.get('content')) == 0:
            censored_word_list = []
            for cw in CensoredWord.objects.all().order_by('censored_word').distinct().values_list('censored_word'):
                if cw[0] in request.POST.get('content'):
                    censored_word_list.append(cw[0])

            if censored_word_list:
                select_forms = CensoredWordSelectForm()
                for cw in censored_word_list:
                    data = [(cw, 'not replace')] + \
                    [(sw.secret_word, sw.secret_word) for sw in CensoredWord.objects.filter(censored_word=cw)]
                    select_forms.fields[cw] = forms.ChoiceField(choices=data, label=cw)
                params_for_confirm['forms'] = select_forms
                return render(request, 'newsns/confirm_comment.html', params_for_confirm)
        else:
            messages.error(request, 'カッコの対応が正しくありません')
            params['content'] = request.POST.get('content')
            return render(request, 'newsns/post.html', params)

        c = Comment()
        c.contributor = request.user
        c.article = Article.objects.get(id=id)
        c.is_article_contributor = request.user == Article.objects.get(id=id).contributor
        c.content = number_brackets(request.POST.get('content'))
        c.save()
        first_posted_comment = Comment.objects.filter(
                                Q(contributor=c.contributor) &
                                Q(article=c.article)).order_by('posted_date').first()
        if first_posted_comment:
            c.first_posted_date = first_posted_comment.posted_date
            c.save()
        messages.success(request, 'コメントを投稿しました')
        return redirect(to='/newsns')
    
    return render(request, 'newsns/post_comment.html', params)

@login_required(login_url='/newsns/login')
def confirm_comment(request):
    if request.method == 'POST':
        if request.POST.get('notpost'):
            params = {
                'login_user':request.user,
                'form':ArticleForm,
                'content':request.POST.get('content'),
            }
            return render(request, 'newsns/post.html', params)
            
        content = request.POST.get('content')
        is_censored_word_contained = True
        is_replaced = False
        while is_censored_word_contained:
            is_censored_word_contained = False
            for cw in CensoredWord.objects.all().distinct().values_list('censored_word').reverse():
                if cw[0] in content:
                    if 'not replace' in request.POST or cw[0] in request.POST:
                        content = content.replace(cw[0], request.POST.get(cw[0]))
                        if CensoredWordHistory.objects.filter(
                            user=request.user,
                            censored_word=CensoredWord.objects.filter(
                                censored_word=cw[0],
                                secret_word=request.POST.get(cw[0])).first()):
                            CensoredWordHistory.objects.filter(
                                user=request.user,
                                censored_word=CensoredWord.objects.filter(
                                    censored_word=cw[0],
                                    secret_word=request.POST.get(cw[0])).first()).first().save()
                        is_censored_word_contained = True
                        continue
                    else:
                        if CensoredWordHistory.objects.filter(
                            user=request.user,
                            censored_word=CensoredWord.objects.filter(
                                censored_word=cw[0],
                                secret_word=request.POST.get(cw[0])).first()):
                            s = CensoredWordHistory.objects.filter(
                                    user=request.user,
                                    censored_word=CensoredWord.objects.filter(
                                        censored_word=cw[0],
                                        secret_word=request.POST.get(cw[0])).first()).first().censored_word.secretword
                        else:
                            s = CensoredWord.objects.filter(censored_word=cw[0]).order_by('?').first().secret_word
                        content = content.replace(cw[0], s)
                    is_censored_word_contained = True
        c = Comment()
        c.contributor = request.user
        c.article = Article.objects.get(id=int(request.POST.get('article_id')))
        c.is_article_contributor = request.user == Article.objects.get(id=int(request.POST.get('article_id'))).contributor
        c.content = number_brackets(content)
        c.save()
        first_posted_comment = Comment.objects.filter(
                                Q(contributor=c.contributor) &
                                Q(article=c.article)).order_by('posted_date').first()
        if first_posted_comment:
            c.first_posted_date = first_posted_comment.posted_date
            c.save()
        messages.success(request, 'コメントを投稿しました')
        return redirect(to='/newsns')

    return redirect(to='/newsns')

def article(request, id):
    params = {
        'login_user':request.user,
        'article':None,
        'comments':None,
    }

    if Article.objects.filter(id=id):
        params['article'] = Article.objects.get(id=id)
        params['comments'] = Comment.objects.filter(article=id)
        
    return render(request, 'newsns/article.html', params)

def censored_word_list(request):
    params = {
        'censord_words':None,
        'search_form':SearchForm(),
        'register_form':RegisterCensoredWordForm(),
    }

    if request.method == 'POST':
        print('keywords', request.POST.get('keywords'))
        print('censored_word', request.POST.get('censored_word'))
        print('secret_word', request.POST.get('secret_word'))
        if request.POST.get('keywords'):
            def f(p):
                q = Q()
                conjunction = Q.AND
                for w in p:
                    if w[0] == '-':
                        denial = True
                    else:
                        denial = False

                    if isinstance(w, list):
                        q.add(f(w), conjunction)
                    elif w == 'OR':
                        conjunction = Q.OR
                        continue
                    elif denial:
                        q.add(~Q(censored_word__icontains=w[1:]), conjunction)
                    else:
                        q.add(Q(censored_word__icontains=w), conjunction)
                    conjunction = Q.AND
                return q

            params['censored_words'] = CensoredWord.objects.filter(f(parser(request.POST.get('keywords')))).distinct().values_list('censored_word')

        if request.POST.get('censored_word'):
            if CensoredWord.is_registerable(request.POST.get('secret_word')) \
            and validate_brackets(request.POST.get('censored_word')) == 0 \
            and validate_brackets(request.POST.get('secret_word')) == 0:
                print('is_registerable')
                cw = CensoredWord()
                cw.censored_word = request.POST.get('censored_word')
                cw.secret_word = put_outermost_brackets(request.POST.get('secret_word'))
                cw.save()

    l = []
    for cw in CensoredWord.objects.all().order_by('censored_word').distinct().values_list('censored_word'):
        l.append(cw[0])
    params['censored_words'] = l

    return render(request, 'newsns/censored_word_list.html', params)

def secret_word_list(request, censored_word=''):
    params = {
        'secret_words':None,
        'search_form':SearchForm(),
        'register_form':RegisterCensoredWordForm(),
        'censored_word':censored_word,
    }

    if request.method == 'POST':
        if request.POST.get('keywords'):
            def f(p):
                q = Q()
                conjunction = Q.AND
                for w in p:
                    if w[0] == '-':
                        denial = True
                    else:
                        denial = False

                    if isinstance(w, list):
                        q.add(f(w), conjunction)
                    elif w == 'OR':
                        conjunction = Q.OR
                        continue
                    elif denial:
                        q.add(~Q(secret_word__icontains=w[1:]), conjunction)
                    else:
                        q.add(Q(secret_word__icontains=w), conjunction)
                    conjunction = Q.AND
                return q

            params['secret_words'] = CensoredWord.objects.filter(Q(censored_word=censored_word) & f(parser(request.POST.get('keywords'))))
            return render(request, 'newsns/secret_word_list.html', params)

        if request.POST.get('secret_word'):
            print('val',validate_brackets(request.POST.get('secret_word')))
            if CensoredWord.is_registerable(request.POST.get('secret_word')) \
                and validate_brackets(request.POST.get('secret_word')) == 0:
                cw = CensoredWord()
                cw.censored_word = CensoredWord.objects.get(word=censored_word)
                cw.secret_word = put_outermost_brackets(request.POST.get('secret_word'))
                cw.save()

    if CensoredWord.objects.filter(censored_word=censored_word):
        l = []
        for sw in CensoredWord.objects.filter(censored_word=censored_word).order_by('secret_word').distinct().values_list('secret_word'):
            l.append(sw[0])
        params['secret_words'] = l

    return render(request, 'newsns/secret_word_list.html', params)

def redirect_to_index(request):
    return redirect(to='/newsns/')

def parser(l):
    def f(l, i=0):
        r = []
        is_quoting = False
        s = ''
        while i < len(l):
            if l[i] == '"':
                if is_quoting:
                    is_quoting = False
                    r.append(s.strip())
                    s = ''
                else:
                    is_quoting = True
                    if l[i - 1] == '-':
                        s += '-'
            elif is_quoting:
                s += l[i] + ' '
            elif l[i] == '(':
                e, i = f(l, i + 1)
                r.append(e)
            elif l[i] == ')':
                return r, i
            elif l[i] == '-':
                pass
            else:
                r.append(l[i])
            i += 1
        return r, i
            
    return f(re.sub('(["\(\)])', ' \\1 ', l).split())[0]

def replace_with_secret_words(content):
    is_contained_censored_word = True
    is_replaced = False
    while is_contained_censored_word:
        is_contained_censored_word = False
        for cw in CensoredWord.objects.all().order_by('word').reverse():
            if cw.word in content:
                content = content.replace(cw.word, SecretWord.objects.filter(censored_word=cw.owrd).order_by('?').first().secret_word)
                is_contained_censored_word = True
                is_replaced = True
    return content

def number_brackets(s):
    r = ''
    i = 0
    nest = 1
    while i < len(s):
        if i < len(s) - 1 and \
            s[i] == '\\' and \
            s[i + 1] in '\\[]「」':
                r += s[i + 1]
                i += 2
                continue
        elif s[i] in '[「':
            r += '[' + str(nest) + ' '
            nest += 1
        elif s[i] in ']」':
            nest -= 1
            r += ' ' + str(nest) + ']'
        else:
            r += s[i]
        i += 1
    return r

def validate_brackets(s):
    nest = 0
    postion = 0
    if s:
        for i, c in enumerate(s):
            if c == '[':
                nest += 1
                if nest == 1:
                    position = i
            elif c == ']':
                nest -= 1

            if nest < 0:
                return i
        if nest > 0:
            return position
    return 0

def put_outermost_brackets(s):
    l = parser(s)
    if len(l) == 1 and isinstance(l[0], list):
        return s
    return '[' + s + ']'
