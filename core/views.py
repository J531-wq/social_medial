from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q
import json

from .models import Post, Comment, Message, Follow, Like
from .forms import PostForm, SignUpForm

User = get_user_model()

# ====================== FEED ======================
@login_required
def feed(request):
    posts = Post.objects.prefetch_related(
        "likes", "comments", "author"
    ).order_by("-created_at")

    all_users = User.objects.exclude(id=request.user.id)

    for post in posts:
        post.total_likes_count = post.likes.count()
        post.is_liked = post.likes.filter(user=request.user).exists()

    return render(request, "core/feed.html", {
        "posts": posts,
        "all_users": all_users
    })


# ====================== LIKE POST ======================
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        like_qs = Like.objects.filter(user=request.user, post=post)

        if like_qs.exists():
            like_qs.delete()
            liked = False
        else:
            Like.objects.create(user=request.user, post=post)
            liked = True

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "liked": liked,
                "total_likes": post.likes.count()
            })

    return redirect(request.META.get("HTTP_REFERER", "/"))


# ====================== SEARCH ======================
@login_required
def search(request):
    query = request.GET.get("q", "")
    users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
    posts = Post.objects.filter(caption__icontains=query).order_by("-created_at")

    return render(request, "core/search.html", {
        "query": query,
        "users": users,
        "posts": posts
    })


# ====================== SIGNUP ======================
def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account created for {user.username}")
            return redirect("login")
        messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()

    return render(request, "core/signup.html", {"form": form})


# ====================== CREATE POST ======================
@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Post created successfully")
            return redirect("feed")
        messages.error(request, "Please correct the errors below")
    else:
        form = PostForm()

    return render(request, "core/create_post.html", {"form": form})


# ====================== POST DETAIL ======================
@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.order_by("created_at")

    return render(request, "core/post_detail.html", {
        "post": post,
        "comments": comments
    })


# ====================== ADD COMMENT ======================
@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            Comment.objects.create(post=post, user=request.user, text=text)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})

    return redirect(request.META.get("HTTP_REFERER", "/"))


# ====================== PROFILE ======================
@login_required
def profile(request, username):
    user_profile = get_object_or_404(User, username=username)

    posts = Post.objects.filter(author=user_profile).order_by("-created_at")
    followers_count = Follow.objects.filter(following=user_profile).count()
    following_count = Follow.objects.filter(follower=user_profile).count()
    is_following = Follow.objects.filter(
        follower=request.user, following=user_profile
    ).exists()

    return render(request, "core/profile.html", {
        "user_profile": user_profile,
        "posts": posts,
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following": is_following
    })


# ====================== FOLLOW TOGGLE ======================
@login_required
def follow_toggle(request, username):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return JsonResponse({"error": "Cannot follow yourself"}, status=400)

    follow_qs = Follow.objects.filter(
        follower=request.user, following=target_user
    )

    if follow_qs.exists():
        follow_qs.delete()
        state = "follow"
    else:
        Follow.objects.create(follower=request.user, following=target_user)
        state = "unfollow"

    return JsonResponse({
        "state": state,
        "followers_count": Follow.objects.filter(following=target_user).count(),
        "following_count": Follow.objects.filter(follower=target_user).count(),
    })


# ====================== CHAT ROOM (PERMANENT DELETE SAFE) ======================
@login_required
def chat_room(request, username):
    other_user = get_object_or_404(User, username=username)

    messages_qs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).exclude(
        deleted_for=request.user
    ).order_by("timestamp")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        last_id = int(request.GET.get("last_id", 0))
        messages = messages_qs.filter(id__gt=last_id)

        return JsonResponse({
            "messages": [
                {
                    "message_id": m.id,
                    "sender": m.sender.username,
                    "content": m.content,
                    "image": m.image.url if m.image else None,
                    "audio": m.audio.url if m.audio else None,
                }
                for m in messages
            ]
        })

    return render(request, "core/chat.html", {
        "other_user": other_user,
        "messages": messages_qs
    })


# ====================== SEND MESSAGE ======================
@login_required
@csrf_exempt
def send_message(request, username):
    receiver = get_object_or_404(User, username=username)

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    content = ""
    if request.content_type == "application/json":
        data = json.loads(request.body)
        content = data.get("content", "").strip()
    else:
        content = request.POST.get("content", "").strip()

    audio = request.FILES.get("audio")
    image = request.FILES.get("image")

    if not content and not audio and not image:
        return JsonResponse({"error": "Empty message"}, status=400)

    msg = Message.objects.create(
        sender=request.user,
        receiver=receiver,
        content=content,
        audio=audio,
        image=image
    )

    return JsonResponse({
        "message_id": msg.id,
        "sender": msg.sender.username,
        "content": msg.content,
        "image": msg.image.url if msg.image else None,
        "audio": msg.audio.url if msg.audio else None,
    })


# ====================== DELETE MESSAGE (FINAL & PERMANENT) ======================
@login_required
@require_POST
def delete_message(request, message_id, action):
    msg = get_object_or_404(Message, id=message_id)

    if request.user not in [msg.sender, msg.receiver]:
        return HttpResponseForbidden()

    if action == "delete_for_me":
        msg.deleted_for.add(request.user)
        return JsonResponse({"success": True})

    if action == "delete_for_everyone":
        if request.user != msg.sender:
            return HttpResponseForbidden()

        msg.delete()
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Invalid action"}, status=400)
