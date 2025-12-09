from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Count

from .models import Post, Comment, Message, Follow, Like
from .forms import PostForm, SignUpForm 

User = get_user_model()

# -------------------- FEED (LIKE BUTTON FIX) --------------------
@login_required
def feed(request):
    posts = Post.objects.prefetch_related('likes', 'comments', 'author').all().order_by('-created_at')
    all_users = User.objects.exclude(id=request.user.id)

    # Add helper attributes for template
    for post in posts:
        post.total_likes_count = post.likes.count()
        post.is_liked = post.likes.filter(id=request.user.id).exists()  # <--- key for heart color

    return render(request, 'core/feed.html', {'posts': posts, 'all_users': all_users})

# -------------------- LIKE POST --------------------
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        like_obj = Like.objects.filter(user=request.user, post=post)
        if like_obj.exists():
            like_obj.delete()
            liked = False
        else:
            Like.objects.create(user=request.user, post=post)
            liked = True

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            new_count = post.likes.count()
            return JsonResponse({
                'liked': liked,
                'total_likes': new_count
            })

    return redirect(request.META.get('HTTP_REFERER', '/'))

# -------------------- SEARCH --------------------
@login_required
def search(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)
    posts = Post.objects.filter(caption__icontains=query).order_by('-created_at')
    return render(request, 'core/search.html', {'query': query, 'users': users, 'posts': posts})

# -------------------- SIGNUP --------------------
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save() 
            messages.success(request, f"Account created for {user.username}! You can now log in.")
            return redirect('login') 
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'core/signup.html', {'form': form}) 

# -------------------- CREATE POST --------------------
@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Your post has been uploaded successfully!")
            return redirect('feed')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PostForm()
    return render(request, 'core/create_post.html', {'form': form})

# -------------------- POST DETAIL --------------------
@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all().order_by('created_at')
    return render(request, 'core/post_detail.html', {'post': post, 'comments': comments})

# -------------------- ADD COMMENT --------------------
@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == "POST":
        text = request.POST.get('text', '').strip()
        if text:
            Comment.objects.create(post=post, user=request.user, text=text)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

    return redirect(request.META.get('HTTP_REFERER', '/'))

# -------------------- PROFILE --------------------
@login_required
def profile(request, username):
    user_profile = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user_profile).order_by('-created_at')

    followers_count = Follow.objects.filter(following=user_profile).count()
    following_count = Follow.objects.filter(follower=user_profile).count()
    is_following = Follow.objects.filter(follower=request.user, following=user_profile).exists()

    context = {
        'user_profile': user_profile,
        'posts': posts,
        'followers_count': followers_count,
        'following_count': following_count,
        'is_following': is_following
    }
    return render(request, 'core/profile.html', context)

# -------------------- FOLLOW TOGGLE --------------------
@login_required
def follow_toggle(request, username):
    if request.method == "POST":
        target_user = get_object_or_404(User, username=username)
        if target_user == request.user:
            return JsonResponse({"error": "Cannot follow yourself."}, status=400)

        follow_obj = Follow.objects.filter(follower=request.user, following=target_user)
        if follow_obj.exists():
            follow_obj.delete()
            state = "follow"
        else:
            Follow.objects.create(follower=request.user, following=target_user)
            state = "unfollow"

        followers_count = Follow.objects.filter(following=target_user).count()
        following_count = Follow.objects.filter(follower=target_user).count()

        return JsonResponse({
            "state": state,
            "followers_count": followers_count,
            "following_count": following_count
        })

    return JsonResponse({"error": "Invalid request"}, status=400)

# -------------------- CHAT ROOM --------------------
@login_required
def chat_room(request, username):
    other_user = get_object_or_404(User, username=username)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        last_id = int(request.GET.get('last_id', 0))
        messages = Message.objects.filter(
            sender__in=[request.user, other_user],
            receiver__in=[request.user, other_user],
            id__gt=last_id
        ).order_by('timestamp')

        messages_data = [
            {
                'message_id': msg.id,
                'sender': msg.sender.username,
                'content': msg.content,
                'image': msg.image.url if msg.image else None,
                'audio': msg.audio.url if msg.audio else None,
            }
            for msg in messages if msg.is_visible_to(request.user)
        ]
        return JsonResponse({'messages': messages_data})

    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by('timestamp')

    messages = [msg for msg in messages if msg.is_visible_to(request.user)]

    return render(request, 'core/chat.html', {'other_user': other_user, 'messages': messages})

# -------------------- SEND MESSAGE --------------------
@login_required
@csrf_exempt
def send_message(request, username):
    receiver = get_object_or_404(User, username=username)

    if request.method == 'POST' and request.FILES:
        content = request.POST.get('content', '').strip()
        audio_file = request.FILES.get('audio')
        image_file = request.FILES.get('image')

        if not content and not audio_file and not image_file:
            return JsonResponse({'error': 'Empty message'}, status=400)

        msg = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            content=content,
            audio=audio_file,
            image=image_file
        )

        return JsonResponse({
            'message_id': msg.id,
            'sender': msg.sender.username,
            'content': msg.content,
            'image': msg.image.url if msg.image else None,
            'audio': msg.audio.url if msg.audio else None,
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            if not content:
                return JsonResponse({'error': 'Empty message'}, status=400)

            msg = Message.objects.create(sender=request.user, receiver=receiver, content=content)

            return JsonResponse({
                'message_id': msg.id,
                'sender': msg.sender.username,
                'content': msg.content,
                'image': None,
                'audio': None,
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)

# -------------------- DELETE MESSAGE --------------------
@login_required
def delete_message(request, message_id, action):
    msg = get_object_or_404(Message, id=message_id)

    if action == "delete_for_me":
        if msg.sender == request.user:
            msg.deleted_for_sender = True
        elif msg.receiver == request.user:
            msg.deleted_for_receiver = True
        msg.save()
    elif action == "delete_for_everyone" and msg.sender == request.user:
        msg.deleted_for_everyone = True
        msg.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect(request.META.get('HTTP_REFERER', '/'))
