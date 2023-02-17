from email.policy import default
from re import T
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Post(models.Model):
    body = models.TextField()
    shared_body = models.TextField(null=True, blank=True)
    created_on = models.DateTimeField(default=timezone.now)
    shared_on = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    shared_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    likes = models.ManyToManyField(User, blank=True, related_name='likes')
    dislikes = models.ManyToManyField(User, blank=True, related_name='dislikes')
    image = models.ManyToManyField('Image', blank=True)
    tags = models.ManyToManyField('Tag', blank=True)

    def create_tags(self):
        for word in self.body.split():
            if word[0] == '#':
                tag = Tag.objects.filter(name=word[1:]).first()
                if tag:
                    self.tags.add(tag.pk)
                else:
                    tag = Tag(name=word[1:])
                    tag.save()
                    self.tags.add(tag.pk)
                self.save()

        if self.shared_body:
            for word in self.shared_body.split():
                if word[0] == '#':
                    tag = Tag.objects.filter(name=word[1:]).first()
                    if tag:
                        self.tags.add(tag.pk)
                    else:
                        tag = Tag(name=word[1:])
                        tag.save()
                        self.tags.add(tag.pk)
                    self.save()

    class Meta:
        ordering = ['-created_on', '-shared_on']


class Comment(models.Model):
    comment = models.TextField()
    created_on = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    likes = models.ManyToManyField(User, blank=True, related_name='comment_likes')
    dislikes = models.ManyToManyField(User, blank=True, related_name='comment_dislikes')
    tags = models.ManyToManyField('Tag', blank=True)

    #Comments which has parent field are children(replies) of a parent comment(actual comment)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='+')
    
    #return the children of a comment. ex. Comment.object.filter(parent=Comment.object.get(pk=pk))
    @property
    def children(self):
        return Comment.objects.filter(parent=self).order_by('-created_on')

    #if self.parent is None, the object is a parent(actual comment) else it is a the children(reply)
    @property
    def is_parent(self):
        if self.parent is None:
            return True
        return False

    def create_tags(self):
        for word in self.comment.split():
            if word[0] == '#':
                tag = Tag.objects.filter(name=word[1:]).first()
                if tag:
                    self.tags.add(tag.pk)
                else:
                    tag = Tag(name=word[1:])
                    tag.save()
                    self.tags.add(tag.pk)
                self.save()

class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True, verbose_name='user', related_name='profile', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    picture = models.ImageField(upload_to='uploads/profile_pictures', default='uploads/profile_pictures/default.jpg', blank=True)
    followers = models.ManyToManyField(User, blank=True, related_name='followers')


class Notification(models.Model):
    # 1. Like 2. Comment 3.Follow 4.DM
    notification_type = models.IntegerField()
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_to', null=True)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_from', null=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    comment = models.ForeignKey('comment', on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    thread = models.ForeignKey('ThreadModel', on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    date= models.DateTimeField(default=timezone.now)
    user_has_seen = models.BooleanField(default=False)


class ThreadModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='+')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='+')

class MessageModel(models.Model):
    thread = models.ForeignKey(ThreadModel, on_delete=models.CASCADE, related_name='messagemodel', blank=True, null=True)
    sender_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    receiver_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    body = models.CharField(max_length=1000)
    image = models.ImageField(upload_to='uploads/message_photo', null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)


class Image(models.Model):
    image = models.ImageField(upload_to='uploads/post_photo', blank=True, null=True)


class Tag(models.Model):
    name = models.CharField(max_length=255)
