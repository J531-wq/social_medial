from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from .forms import SignUpForm, PostForm
from .models import User, Post, Like, Comment, Follow, Message

# ---------------------- AUTH & POSTS ----------------------

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("feed")
    else:
        form = SignUpForm()
    return render(request, "core/signup.html", {"form": form})


@login_required
def feed(request):
    following_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    posts = Post.objects.filter(author__id__in=list(following_ids) + [request.user.id])

    all_users = User.objects.exclude(id=request.user.id)

    return render(request, "core/feed.html", {
        "posts": posts,
        "all_users": all_users,
    })


@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("feed")
    else:
        form = PostForm()
    return render(request, "core/create_post.html", {"form": form})


@login_required
def profile(request, username):
    user_profile = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user_profile)
    is_following = Follow.objects.filter(follower=request.user, following=user_profile).exists()
    followers_count = Follow.objects.filter(following=user_profile).count()
    following_count = Follow.objects.filter(follower=user_profile).count()

    context = {
        "user_profile": user_profile,
        "posts": posts,
        "is_following": is_following,
        "followers_count": followers_count,
        "following_count": following_count,
    }
    return render(request, "core/profile.html", context)


@login_required
def follow_toggle(request, username):
    if request.method == "POST":
        target = get_object_or_404(User, username=username)
        if target == request.user:
            return JsonResponse({"error": "You cannot follow yourself"}, status=400)

        follow_obj, created = Follow.objects.get_or_create(follower=request.user, following=target)
        if not created:
            follow_obj.delete()
            state = "unfollowed"
        else:
            state = "followed"

        followers_count = Follow.objects.filter(following=target).count()
        return JsonResponse({"state": state, "followers_count": followers_count})

    return JsonResponse({"error": "POST required"}, status=400)


# ---------------------- CHAT & MESSAGES ----------------------

@login_required
def chat_room(request, username):
    other_user = get_object_or_404(User, username=username)

    messages = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by("timestamp")

    # Filter out messages deleted for the current user
    visible_messages = [
        m for m in messages
        if not ((m.sender == request.user and m.deleted_for_sender) or
                (m.receiver == request.user and m.deleted_for_receiver) or
                m.deleted_for_everyone)
    ]

    return render(request, "core/chat.html", {"other_user": other_user, "messages": visible_messages})


@login_required
@csrf_exempt
def send_message(request, username):
    if request.method == "POST":
        receiver_user = get_object_or_404(User, username=username)
        content = request.POST.get("content", "").strip()
        audio_file = request.FILES.get("audio")
        image_file = request.FILES.get("image")

        if not content and not audio_file and not image_file:
            return JsonResponse({"error": "Message cannot be empty"}, status=400)

        message = Message.objects.create(sender=request.user, receiver=receiver_user, content=content)

        if audio_file:
            message.audio.save(audio_file.name, audio_file)
        if image_file:
            message.image.save(image_file.name, image_file)

        return JsonResponse({
            "status": "sent",
            "message_id": message.id,
            "content": message.content,
            "audio": message.audio.url if audio_file else None,
            "image": message.image.url if image_file else None,
            "timestamp": message.timestamp.strftime("%H:%M"),
            "sender": request.user.username,
        })

    return HttpResponseBadRequest("Invalid request")


@login_required
@csrf_exempt
def delete_message(request, message_id, action):
    """Delete a message for me or for everyone."""
    message = get_object_or_404(Message, id=message_id)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    # --- DELETE FOR ME ---
    if action == "delete_for_me":
        if request.user == message.sender:
            message.deleted_for_sender = True
        elif request.user == message.receiver:
            message.deleted_for_receiver = True
        else:
            return JsonResponse({"error": "Not allowed"}, status=403)
        message.save()
        return JsonResponse({"status": "deleted_for_me"})

    # --- DELETE FOR EVERYONE ---
    elif action == "delete_for_everyone":
        if request.user != message.sender:
            return JsonResponse({"error": "Only sender can delete for everyone"}, status=403)

        message.deleted_for_everyone = True

        if message.audio:
            message.audio.delete(save=False)
        if message.image:
            message.image.delete(save=False)

        message.save()
        return JsonResponse({"status": "deleted_for_everyone"})

    else:
        return JsonResponse({"error": "Invalid action"}, status=400)


# ---------------------- LIKES & COMMENTS ----------------------

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return redirect("post_detail", post_id=post.id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        text = request.POST.get("text")
        if text:
            Comment.objects.create(user=request.user, post=post, text=text)
    return redirect("post_detail", post_id=post.id)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all().order_by("-created_at")
    return render(request, "core/post_detail.html", {"post": post, "comments": comments})
