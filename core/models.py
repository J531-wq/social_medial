from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# ======================================================
# USER
# ======================================================
class User(AbstractUser):
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True
    )

    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
        default="profiles/default.png"
    )

    bio = models.TextField(blank=True)

    def __str__(self):
        return self.username

    @property
    def profile_image_url(self):
        try:
            return self.profile_image.url
        except Exception:
            return "/media/profiles/default.png"


# ======================================================
# POSTS
# ======================================================
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
        return f"{self.author.username}'s post"


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    post = models.ForeignKey(
        Post,
        related_name="likes",
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    post = models.ForeignKey(
        Post,
        related_name="comments",
        on_delete=models.CASCADE
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


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


# ======================================================
# MESSAGES (PERMANENT DELETE, PRODUCTION SAFE)
# ======================================================
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

    content = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to="chat_images/",
        blank=True,
        null=True
    )
    audio = models.FileField(
        upload_to="chat_audio/",
        blank=True,
        null=True
    )

    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    # 🔥 Permanent delete-for-me support
    deleted_for = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="deleted_messages"
    )

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["sender", "receiver", "timestamp"]),
        ]

    def __str__(self):
        return f"Message {self.id} ({self.sender} → {self.receiver})"

    def is_visible_to(self, user):
        """
        Safety helper — optional.
        Queries should already exclude deleted messages.
        """
        return user not in self.deleted_for.all()
