from django.http import HttpResponseRedirect, HttpResponse
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect, render
from .models import Post, Comment, UserProfile, Notification, ThreadModel, MessageModel, Image, Tag
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from .forms import PostForm, CommentForm, ThreadForm, MessageForm, ShareForm, ExploreForm

from django.views import View
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your views here.

class PostListView(LoginRequiredMixin, View):
    login_url = 'account_login'
    def get(self, request, *args, **kwargs):
        posts = Post.objects.filter(
            author__profile__followers__in=[request.user]
        )
        form = PostForm()
        shareform = ShareForm()
        context = {
            'post_list': posts,
            'form': form,
            'shareform': shareform,
        }
        return render(request, 'social/post_list.html', context)

    def post(self, request, *args, **kwargs):
        posts = Post.objects.all().order_by('-created_on')
        form = PostForm(request.POST, request.FILES)
        images = request.FILES.getlist('image')
        shareform = ShareForm()
        print(images)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = self.request.user
            new_post.save()
            new_post.create_tags()
            for image in images:
                img = Image(image=image)
                img.save()
                new_post.image.add(img)
            new_post.save()

        context = {
            'post_list':posts,
            'form': form,
            'shareform': shareform,
        }
        return render(request, 'social/post_list.html', context)

class SharedPostView(View):
    def post(self, request, pk, *args, **kwargs):
        original_post = Post.objects.get(pk=pk)
        form = ShareForm(request.POST)

        if form.is_valid():
            new_post = Post(
                body=original_post.body,
                shared_body=request.POST.get('body'),
                created_on=original_post.created_on,
                shared_on=timezone.now(),
                author=original_post.author,
                shared_user=request.user
            )
            new_post.save()

            for img in original_post.image.all():
                new_post.image.add(img)
            new_post.save()
            return redirect('post-list')


class PostDetailView(LoginRequiredMixin, View):
    login_url = 'account_login'
    def get(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        post = Post.objects.get(pk=pk)
        form = CommentForm()
        comments = Comment.objects.filter(post=post)

        context = {
            'post': post,
            'form': form,
            'comments': comments,
        }
        return render(request, 'social/post_detail.html', context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        post = Post.objects.get(pk=pk)
        form = CommentForm(self.request.POST)
        comments = Comment.objects.filter(post=post)
        
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.author = self.request.user
            new_comment.post = post
            new_comment.save()
            notification = Notification(notification_type=2, to_user=post.author, from_user=request.user, post=post)
            notification.save()
            new_comment.create_tags()

        context = {
            'post': post,
            'form': form,
            'comments': comments,
        }
        
        return render(request, 'social/post_detail.html', context)


class CommentReplyView(LoginRequiredMixin, View):
    def post(self, request, post_pk, pk, *args, **kwargs):
        print(post_pk)
        post = Post.objects.get(pk=post_pk)
        parent_comment = Comment.objects.get(pk=pk)
        author = request.user
        form = CommentForm(request.POST)
        new_comment = form.save(commit=False)
        new_comment.post = post 
        new_comment.parent = parent_comment
        new_comment.author = author
        new_comment.save()

        notification = Notification(notification_type=2, to_user=parent_comment.author, from_user=request.user, comment=parent_comment)
        notification.save()
        return redirect('post-detail', pk=post_pk)


class PostEditView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Post
    fields = ['body']
    template_name = 'social/post_edit.html'
    login_url = 'account_login'

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('post-detail', kwargs={'pk': pk})

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.author

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Post
    template_name = 'social/post_delete.html'
    login_url = 'account_login'
    success_url = reverse_lazy('post-list')

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.author

class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Comment
    template_name = 'social/comment_delete.html'
    login_url = 'account_login'
    def get_success_url(self):
        pk = self.kwargs['post_pk']
        return reverse_lazy('post-detail', kwargs={'pk': pk})

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.author

class ProfileView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        user = profile.user
        posts = Post.objects.filter(author=user)
        followers = profile.followers.all()
        number_of_followers = followers.count()
        is_following = request.user in followers
        print(is_following)

        context = {
            'profile': profile,
            'user': user,
            'posts': posts,
            'number_of_followers': number_of_followers,
            'is_following': is_following,
        }

        return render(request, 'social/profile.html', context)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance,created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class ProfileEditView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = UserProfile
    fields = ['name', 'location', 'birth_date', 'bio', 'picture']
    template_name = 'social/profile_edit.html'

    def test_func(self):
        return self.request.user == self.get_object().user

    def get_success_url(self):
        pk = self.kwargs['pk']
        return reverse_lazy('profile', kwargs = {'pk': pk})

class AddFollower(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        profile.followers.add(request.user)

        notification = Notification(notification_type=3, to_user=profile.user, from_user=request.user)
        notification.save()

        return redirect('profile', pk=pk)

class RemoveFollower(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        profile.followers.remove(request.user)

        return redirect('profile', pk=pk)


class AddLike(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk)
        dislikes = post.dislikes.all()
        is_dislike = request.user in dislikes
        if is_dislike:
            post.dislikes.remove(request.user)
        likes = post.likes.all()
        is_like = request.user in likes
        if is_like:
            post.likes.remove(request.user)
        else:
            post.likes.add(request.user)
            notification = Notification(notification_type=1, to_user=post.author, from_user=request.user, post=post)
            notification.save()

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)


class AddDislike(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        post = Post.objects.get(pk=pk)
        likes = post.likes.all()
        is_like = request.user in likes
        if is_like:
            post.likes.remove(request.user)
        dislikes = post.dislikes.all()
        is_dislike = request.user in dislikes
        if is_dislike:
            post.dislikes.remove(request.user)
        else:
            post.dislikes.add(request.user)

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)


class AddCommentLike(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        comment = Comment.objects.get(pk=pk)
        dislikes = comment.dislikes.all()
        is_dislike = request.user in dislikes
        if is_dislike:
            comment.dislikes.remove(request.user)
        likes = comment.likes.all()
        is_like = request.user in likes
        if is_like:
            comment.likes.remove(request.user)
        else:
            comment.likes.add(request.user)
            notification = Notification(notification_type=1, to_user=comment.author, from_user=request.user, comment=comment)
            notification.save()

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)


class AddCommentDislike(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        comment = Comment.objects.get(pk=pk)
        likes = comment.likes.all()
        is_like = request.user in likes
        if is_like:
            comment.likes.remove(request.user)
        dislikes = comment.dislikes.all()
        is_dislike = request.user in dislikes
        if is_dislike:
            comment.dislikes.remove(request.user)
        else:
            comment.dislikes.add(request.user)

        next = request.POST.get('next', '/')
        return HttpResponseRedirect(next)


class UserSearch(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query = request.GET['query']
        profile_list = UserProfile.objects.filter(Q(user__username__icontains = query))

        context = {
            'profile_list': profile_list,
        }
        return render(request, 'social/search.html', context)

class ListFollowers(View):
    def get(self, request, pk, *args, **kwargs):
        profile = UserProfile.objects.get(pk=pk)
        followers = profile.followers.all()

        context = {
            'profile': profile,
            'followers': followers,
        }

        return render(request, 'social/followers_list.html', context)

class PostNotification(View):
    def get(self, request, notification_pk, post_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        post = Post.objects.get(pk=post_pk)

        notification.user_has_seen = True
        notification.save()
        return redirect('post-detail', pk=post_pk)

class FollowNotification(View):
    def get(self, request, notification_pk, profile_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        profile = UserProfile.objects.get(pk=profile_pk)

        notification.user_has_seen = True
        notification.save()
        return redirect('profile', pk=profile_pk)

class ThreadNotification(View):
    def get(self, request, notification_pk, thread_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        thread = ThreadModel.objects.get(pk=thread_pk)

        notification.user_has_seen = True
        notification.save()
        return redirect('thread', pk=thread_pk)

class RemoveNotification(View):
    def delete(self, request, notification_pk, *args, **kwargs):
        notification = Notification.objects.get(pk=notification_pk)
        notification.user_has_seen = True
        notification.save()
        return HttpResponse('Success', content_type='text/plain')


class ListThreads(View):
    def get(self, request, *args, **kwargs):
        threads = ThreadModel.objects.filter(Q(user=request.user) | Q(receiver=request.user))
        context = {
            'threads': threads,
        }

        return render(request, 'social/inbox.html', context)

class CreateThread(View):
    def get(self, request, *args, **kwargs):
        form = ThreadForm()

        context = {
            'form': form,
        }

        return render(request, 'social/create_thread.html', context)

    def post(self, request, *args, **kwargs):
        form = ThreadForm(request.POST)
        username = request.POST['username']

        try:
            receiver = User.objects.get(username=username)
            if ThreadModel.objects.filter(user=request.user, receiver=receiver).exists():
                thread = ThreadModel.objects.filter(user=request.user, receiver=receiver)[0]
                return redirect('thread', pk=thread.pk)
            elif ThreadModel.objects.filter(user=receiver, receiver=request.user):
                thread = ThreadModel.objects.filter(user=receiver, receiver=request.user)[0]
                return redirect('thread', pk=thread.pk)

            if form.is_valid():
                thread = ThreadModel(user=request.user, receiver=receiver)
                thread.save()
                return redirect('thread', pk=thread.pk)
        except:
            messages.error(request, 'Invalid Username')
            return redirect('create-thread')


class ThreadView(View):
    def get(self, request, pk, *args, **kwargs):
        thread = ThreadModel.objects.get(pk=pk)
        form = MessageForm()
        print(form)
        message_list = thread.messagemodel.all()

        context = {
            'thread': thread,
            'form': form,
            'message_list': message_list,
        }

        return render(request, 'social/thread.html', context) 

class CreateMessage(View):
    def post(self, request, pk, *args, **kwargs):
        form = MessageForm(request.POST, request.FILES)
        thread = ThreadModel.objects.get(pk=pk)
        # body = request.POST['message']
        sender_user = request.user
        if thread.user == request.user:
            receiver_user = thread.receiver
        else:
            receiver_user = thread.user 
        
        if form.is_valid():
            message = form.save(commit=False)
            message.thread = thread
            message.sender_user = sender_user
            message.receiver_user = receiver_user
            message.save()

        # message = MessageModel(
        #     thread=thread,
        #     sender_user=sender_user,
        #     receiver_user=receiver_user,
        #     body=body,
        # )
        # message.save()
        Notification.objects.create(
            notification_type=4,
            from_user=request.user,
            to_user=receiver_user,
            thread=thread,
        )
        return redirect('thread', pk=pk)


class Explore(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('query')
        explore_form = ExploreForm()
        tag = Tag.objects.filter(name__icontains=query).first() if query else None
        if tag:
            posts = Post.objects.filter(tags__in=[tag])
        else:
            posts = Post.objects.all()

        context = {
            'tag': tag,
            'posts': posts,
            'explore_form': explore_form,
        }

        return render(request, 'social/explore.html', context)

