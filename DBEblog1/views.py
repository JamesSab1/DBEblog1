from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.core.mail import send_mail
from django.db.models import Count

from taggit.models import Tag
from haystack.query import SearchQuerySet

from .models import Post, Comment
from .forms import EmailPostForm, CommentForm, SearchForm


# def post_list(request):
##    object_list = Post.published.all()
##    posts = Post.published.all()
# return render(request, 'DBEblog1/post/list.html', {'posts':posts})


def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 5)  # 5 posts each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver the last page of results
        posts = paginator.page(paginator.num_pages)
    return render(request, 'DBEblog1/post/list.html', {'page': page,
                                                       'posts': posts,
                                                       'tag': tag})


# class PostListView(ListView):
##    queryset = Post.published.all()
##    context_object_name = 'posts'
##    paginate_by = 3
##    template_name = 'DBEblog1/post/list.html'


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published',
                             publish__year=year, publish__month=month,
                             publish__day=day)
    # List of active comments for this post
    comments = post.comments.filter(active=True)
    new_comment = False

    if request.method == 'POST':
        # A comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # create Comment object but don't save it yet
            new_comment = comment_form.save(commit=False)
            # assign current post to the comment
            new_comment.post = post
            # save
            new_comment.save()
    else:
        comment_form = CommentForm()

    # list of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]

    return render(request, 'DBEblog1/post/detail.html', {'post': post,
                                                         'comments': comments,
                                                         'comment_form': comment_form,
                                                         'new_comment': new_comment,
                                                         'similar_posts': similar_posts})


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    recipient = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{} ({}) recommends you reading "{}"'.format(cd['name'], cd['email'], post.title)
            message = 'Read "{}" at {}\n\n{}\'s comments: {}'.format(post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'jamessab71@gmail.com', [cd['to']])
            recipient = cd['to']
            sent = True
    else:
        form = EmailPostForm()

    return render(request, 'DBEblog1/post/share.html', {'post': post,
                                                        'form': form,
                                                        'sent': sent,
                                                        'recipient': recipient})


def post_search(request):
    form = SearchForm()
    cd = None
    results = None
    total_results = None
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            cd = form.cleaned_data
            results = SearchQuerySet().models(Post).filter(content=cd['query']).load_all()
            # count total results
            total_results = results.count()
    return render(request, 'DBEblog1/post/search.html',
                  {'form': form, 'cd': cd, 'results': results, 'total_results': total_results})
