from django.contrib import admin
from .models import User, Post, Follow, Message, Comment, Like

admin.site.register(User)
admin.site.register(Post)
admin.site.register(Follow)
admin.site.register(Message)
admin.site.register(Comment)
admin.site.register(Like)
