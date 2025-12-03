from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# ---------------------- USER (FIXED) ----------------------
class User(AbstractUser):
    # ADDED: Field to store the user's phone number
    phone_number = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        unique=True # Optional: ensures that no two users have the same phone number
    )
    
    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
        default="profiles/default.png" # safe default
    )
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.username

    # Safe image accessor
    @property
    def profile_image_url(self):
        """
        Always returns a valid image URL.
        Prevents ValueError: 'profile_image' has no file associated.
        """
        try:
            return self.profile_image.url
        except:
            return "/media/profiles/default.png"


# ---------------------- POSTS ----------------------
class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="posts",
        on_delete=models.CASCADE
    )
    image = models.ImageField(
        upload_to="posts/",
        blank=True,
        null=True
    )
    caption = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_likes(self):
        return self.likes.count()

    def total_comments(self):
        return self.comments.count()

    def __str__(self):
        return f"{self.author.username}'s Post"


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="likes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")  # prevent duplicate likes


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="following_set",
        on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="followers_set",
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")


# ---------------------- MESSAGES ----------------------
class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="sent_messages",
        on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="received_messages",
        on_delete=models.CASCADE
    )
    content = models.TextField(default="", blank=True)
    image = models.ImageField(upload_to="chat_images/", blank=True, null=True)
    audio = models.FileField(upload_to="chat_audio/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    deleted_for_sender = models.BooleanField(default=False)
    deleted_for_receiver = models.BooleanField(default=False)
    deleted_for_everyone = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver} at {self.timestamp}"

    def is_visible_to(self, user):
        if self.deleted_for_everyone:
            return False
        if user == self.sender and self.deleted_for_sender:
            return False
        if user == self.receiver and self.deleted_for_receiver:
            return False
        return True