import uuid
from pathlib import Path

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Count, Prefetch, Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegisterForm, LoginForm, UserUpdateForm, PostCreateForm, CommentForm
from django.contrib.auth.forms import PasswordChangeForm
from .models import (
    Comment,
    Conversation,
    CustomUser,
    Message,
    Notification,
    Post,
)

# Create your views here.


def register_page(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_page(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


@require_POST
def logout_page(request):
    logout(request)
    return redirect('login')


def _create_notification(request, recipient, actor, notification_type, post=None, comment=None):
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        post=post,
        comment=comment,
    )
    html = render_to_string(
        'partials/notification_item.html',
        {'notification': notification},
        request=request,
    )
    unread_count = Notification.objects.filter(
        recipient=recipient,
        is_read=False,
    ).count()
    async_to_sync(get_channel_layer().group_send)(
        f'notifications_{recipient.pk.hex}',
        {
            'type': 'notification_event',
            'data': {
                'type': 'notification',
                'html': html,
                'unread_count': unread_count,
                'message': {
                    Notification.LIKE: 'yangi like bildirishnomasi',
                    Notification.COMMENT: 'yangi izoh bildirishnomasi',
                    Notification.FOLLOW: 'yangi obuna bildirishnomasi',
                }[notification_type],
                'actor_username': actor.username,
                'notification_type': notification_type,
                'notifications_url': reverse('notifications'),
            },
        },
    )
    return notification



@require_GET
def home_page(request):
    posts = get_post_feed(request.user)
    return render(request, 'index.html', {'posts': posts})


@login_required
def profile_page(request, username=None):
    profile_user = (
        get_object_or_404(CustomUser, username=username) if username else request.user
    )
    is_own_profile = profile_user == request.user
    if request.method == 'POST':
        if not is_own_profile:
            return HttpResponseForbidden()
        form = PostCreateForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('profile')
    else:
        form = PostCreateForm() if is_own_profile else None

    posts = get_post_feed(request.user, Post.objects.filter(author=profile_user))
    is_following = (
        request.user.following.filter(pk=profile_user.pk).exists()
        if not is_own_profile
        else False
    )
    return render(
        request,
        'profile.html',
        {
            'profile_user': profile_user,
            'posts': posts,
            'form': form,
            'is_own_profile': is_own_profile,
            'is_following': is_following,
            'followers_count': profile_user.followers.count(),
            'following_count': profile_user.following.count(),
        },
    )



@login_required
def add_post_page(request, username=None):
    profile_user = (
        get_object_or_404(CustomUser, username=username) if username else request.user
    )
    is_own_profile = profile_user == request.user
    if request.method == 'POST':
        if not is_own_profile:
            return HttpResponseForbidden()
        form = PostCreateForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('profile')
    else:
        form = PostCreateForm() if is_own_profile else None

    posts = get_post_feed(request.user, Post.objects.filter(author=profile_user))
    is_following = (
        request.user.following.filter(pk=profile_user.pk).exists()
        if not is_own_profile
        else False
    )
    return render(
        request,
        'add_post.html',
        {
            'profile_user': profile_user,
            'posts': posts,
            'form': form,
            'is_own_profile': is_own_profile,
            'is_following': is_following,
            'followers_count': profile_user.followers.count(),
            'following_count': profile_user.following.count(),
        },
    )




@login_required
def update_profile_page(request):
    profile_form = UserUpdateForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=request.user,
    )

    if request.method == 'POST' and profile_form.is_valid():
        profile_form.save()
        return redirect('home')

    return render(request, 'update_profile.html', {'profile_form': profile_form})


@login_required
def update_password_page(request):
    password_form = PasswordChangeForm(
        request.user,
        request.POST if request.method == 'POST' else None,
    )
    password_form.fields['old_password'].label = 'Joriy parol'
    password_form.fields['new_password1'].label = 'Yangi parol'
    password_form.fields['new_password2'].label = 'Yangi parolni tasdiqlang'
    password_form.fields['new_password1'].help_text = (
        'Parolingiz kamida 8 ta belgidan iborat bo‘lsin va keng tarqalgan '
        'yoki faqat raqamlardan tashkil topgan bo‘lmasin.'
    )
    password_form.fields['new_password2'].help_text = (
        'Tasdiqlash uchun yangi parolni yana bir bor kiriting.'
    )

    if request.method == 'POST' and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        return redirect('home')

    return render(request, 'update_password.html', {'password_form': password_form})



@login_required
@require_POST
def like_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
        if post.author_id != request.user.pk:
            _create_notification(
                request,
                post.author,
                request.user,
                Notification.LIKE,
                post=post,
            )
    if _is_ajax(request):
        return _post_card_json(request, post)
    return _safe_return(request)


@login_required
@require_POST
def add_comment_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        if post.author_id != request.user.pk:
            _create_notification(
                request,
                post.author,
                request.user,
                Notification.COMMENT,
                post=post,
                comment=comment,
            )
        if _is_ajax(request):
            return _post_card_json(request, post)
    elif _is_ajax(request):
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    return _safe_return(request)


@login_required
@require_POST
def follow_toggle_view(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)
    if target_user != request.user:
        if request.user.following.filter(id=target_user.id).exists():
            request.user.following.remove(target_user)
        else:
            request.user.following.add(target_user)
            _create_notification(
                request,
                target_user,
                request.user,
                Notification.FOLLOW,
            )
    if _is_ajax(request):
        return JsonResponse({
            'is_following': request.user.following.filter(pk=target_user.pk).exists(),
            'followers_count': target_user.followers.count(),
            'following_count': target_user.following.count(),
        })
    return _safe_return(request)


def get_post_feed(user, queryset=None):
    posts = queryset if queryset is not None else Post.objects.all()
    return (
        posts.select_related('author')
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            share_count=Count('shared_messages', distinct=True),
        )
        .prefetch_related(
            Prefetch(
                'likes',
                queryset=(
                    CustomUser.objects.filter(pk=user.pk)
                    if user.is_authenticated
                    else CustomUser.objects.none()
                ),
                to_attr='liked_by_user',
            ),
            Prefetch(
                'comments',
                queryset=Comment.objects.select_related('author')
                .prefetch_related('author__socialaccount_set')
                .order_by('-created_at')[:3],
                to_attr='recent_comments',
            ),
            'author__socialaccount_set',
        )
    )


def _safe_return(request):
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referer)
    return redirect('home')


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _post_card_json(request, post):
    refreshed_post = get_post_feed(
        request.user,
        Post.objects.filter(pk=post.pk),
    ).get()
    return JsonResponse({
        'html': render_to_string(
            'partials/post_card.html',
            {'post': refreshed_post},
            request=request,
        ),
    })



@login_required
@require_GET
def search_users_page(request):
    query = request.GET.get('q', '').strip()
    users = (
        CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        .exclude(pk=request.user.pk)
        .prefetch_related('socialaccount_set')
        .order_by('username')[:20]
        if query
        else CustomUser.objects.none()
    )
    users_html = ''.join(
        render_to_string(
            'partials/search_user_result.html',
            {'user_result': user},
            request=request,
        )
        for user in users
    )
    return JsonResponse({'html': users_html, 'count': len(users)})


@login_required
@require_GET
def user_connections_view(request, username, connection_type):
    profile_user = get_object_or_404(CustomUser, username=username)
    if connection_type == 'following':
        users = profile_user.following.all()
        title = 'Obuna bo‘lganlar'
    elif connection_type == 'followers':
        users = profile_user.followers.all()
        title = 'Obunachilar'
    else:
        raise Http404('Bunday obuna ro‘yxati mavjud emas.')

    users = list(
        users.prefetch_related('socialaccount_set').order_by('username')
    )
    html = render_to_string(
        'partials/connection_user.html',
        {'users': users},
        request=request,
    )
    return JsonResponse({'html': html, 'count': len(users), 'title': title})


@login_required
@require_GET
def notifications_page(request):
    notifications = list(
        Notification.objects.filter(recipient=request.user)
        .select_related(
            'actor',
            'post',
            'post__author',
            'comment',
            'comment__post',
        )
        .prefetch_related('actor__socialaccount_set')
        .order_by('-created_at')[:100]
    )
    for notification in notifications:
        if notification.notification_type == Notification.FOLLOW:
            notification.target_url = reverse(
                'user_profile',
                args=[notification.actor.username],
            )
        elif notification.post_id:
            notification.target_url = (
                f"{reverse('home')}#post-{notification.post_id}"
            )
        else:
            notification.target_url = reverse('home')
    return render(
        request,
        'notifications.html',
        {'notifications': notifications},
    )


@login_required
@require_POST
def open_notification_view(request, notification_id):
    notification = get_object_or_404(
        Notification.objects.select_related('actor', 'post'),
        pk=notification_id,
        recipient=request.user,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read', 'updated_at'])
    if notification.notification_type == Notification.FOLLOW:
        return redirect('user_profile', username=notification.actor.username)
    if notification.post_id:
        return redirect(f"{reverse('home')}#post-{notification.post_id}")
    return redirect('home')


@login_required
@require_POST
def mark_notifications_read_view(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)
    return redirect('notifications')


@login_required
@require_GET
def chat_page(request, username=None):
    target_user = (
        get_object_or_404(CustomUser, username=username) if username else None
    )
    if target_user and target_user.pk == request.user.pk:
        raise Http404('O‘zingiz bilan chat ochib bo‘lmaydi.')

    if target_user:
        selected_conversation, _ = Conversation.get_or_create_direct(
            request.user,
            target_user,
        )
    else:
        selected_conversation = None

    if selected_conversation:
        Message.objects.filter(
            conversation=selected_conversation,
            read_at__isnull=True,
        ).exclude(sender=request.user).update(read_at=timezone.now())

    conversations = list(
        Conversation.objects.filter(
            Q(member_one=request.user) | Q(member_two=request.user)
        )
        .annotate(
            unread_count=Count(
                'messages',
                filter=(
                    Q(messages__read_at__isnull=True)
                    & ~Q(messages__sender=request.user)
                ),
            ),
        )
        .select_related('member_one', 'member_two')
        .prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.select_related('sender')
                .order_by('-created_at')[:1],
                to_attr='latest_messages',
            ),
            'member_one__socialaccount_set',
            'member_two__socialaccount_set',
        )
    )
    for conversation in conversations:
        conversation.chat_peer = conversation.other_member(request.user)
        conversation.latest_message = (
            conversation.latest_messages[0]
            if conversation.latest_messages
            else None
        )
        if conversation.latest_message:
            latest = conversation.latest_message
            latest.preview_text = latest.body or {
                'image': '📷 Rasm',
                'video': '🎬 Video',
                'audio': '🎙 Ovozli xabar',
                Message.SHARE: '📄 Post ulashildi',
            }.get(latest.attachment_type, '')

    peer = (
        selected_conversation.other_member(request.user)
        if selected_conversation
        else None
    )
    messages = []
    if selected_conversation:
        messages = list(
            selected_conversation.messages
            .select_related('sender', 'shared_post', 'shared_post__author')
            .prefetch_related('sender__socialaccount_set')
            .order_by('-created_at')[:100]
        )
        messages.reverse()

    return render(
        request,
        'chat.html',
        {
            'conversations': conversations,
            'selected_conversation': selected_conversation,
            'chat_peer': peer,
            'messages': messages,
        },
    )


@login_required
@require_POST
def upload_chat_media_view(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.filter(
            Q(member_one=request.user) | Q(member_two=request.user),
        ),
        pk=conversation_id,
    )
    uploaded_file = request.FILES.get('file')
    attachment_type = request.POST.get('attachment_type')
    accepted_types = {
        'image': {
            'image/jpeg': ('.jpg', 10 * 1024 * 1024),
            'image/png': ('.png', 10 * 1024 * 1024),
            'image/webp': ('.webp', 10 * 1024 * 1024),
            'image/gif': ('.gif', 10 * 1024 * 1024),
        },
        'video': {
            'video/mp4': ('.mp4', 50 * 1024 * 1024),
            'video/webm': ('.webm', 50 * 1024 * 1024),
            'video/quicktime': ('.mov', 50 * 1024 * 1024),
        },
        'audio': {
            'audio/webm': ('.webm', 15 * 1024 * 1024),
            'audio/ogg': ('.ogg', 15 * 1024 * 1024),
            'audio/mp4': ('.m4a', 15 * 1024 * 1024),
            'audio/mpeg': ('.mp3', 15 * 1024 * 1024),
            'audio/wav': ('.wav', 15 * 1024 * 1024),
        },
    }
    if not uploaded_file or attachment_type not in accepted_types:
        return JsonResponse(
            {'error': 'Yuboriladigan fayl topilmadi yoki turi noto‘g‘ri.'},
            status=400,
        )

    mime_type = uploaded_file.content_type
    allowed_mime_types = accepted_types[attachment_type]
    if mime_type not in allowed_mime_types:
        return JsonResponse(
            {'error': 'Bu turdagi faylni yuborib bo‘lmaydi.'},
            status=400,
        )

    extension, max_size = allowed_mime_types[mime_type]
    if uploaded_file.size > max_size:
        return JsonResponse(
            {'error': 'Fayl hajmi ruxsat etilgan chegaradan oshdi.'},
            status=413,
        )

    uploaded_file.name = f'{uuid.uuid4().hex}{extension}'
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        body='',
        attachment_type=attachment_type,
        media=uploaded_file,
    )
    Conversation.objects.filter(pk=conversation.pk).update(
        updated_at=timezone.now(),
    )
    sender = request.user
    message_data = {
        'type': 'message',
        'id': str(message.pk),
        'body': message.body,
        'attachment_type': message.attachment_type,
        'media_url': reverse('chat_media', args=[message.pk]),
        'sender': sender.username,
        'sender_id': str(sender.pk),
        'sender_avatar': sender.avatar_url,
        'profile_url': reverse('user_profile', args=[sender.username]),
        'created_at': message.created_at.isoformat(),
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{conversation.pk.hex}',
        {'type': 'chat_message', 'data': message_data},
    )
    return JsonResponse(message_data, status=201)


@login_required
@require_POST
def chat_message_action_view(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related('conversation'),
        pk=message_id,
        sender=request.user,
        conversation__in=Conversation.objects.filter(
            Q(member_one=request.user) | Q(member_two=request.user),
        ),
    )
    action = request.POST.get('action')
    conversation_id = message.conversation_id
    if action == 'edit':
        body = request.POST.get('body', '').strip()
        if not body:
            return JsonResponse(
                {'error': 'Xabar matni bo‘sh bo‘lmasligi kerak.'},
                status=400,
            )
        if len(body) > 2000:
            return JsonResponse(
                {'error': 'Xabar 2000 belgidan oshmasligi kerak.'},
                status=400,
            )
        message.body = body
        message.save(update_fields=['body', 'updated_at'])
        payload = {
            'type': 'message_updated',
            'id': str(message.pk),
            'body': message.body,
            'sender_id': str(request.user.pk),
        }
    elif action == 'delete':
        media_name = message.media.name if message.media else None
        message_id_value = str(message.pk)
        storage = message.media.storage if message.media else None
        message.delete()
        if media_name and storage:
            storage.delete(media_name)
        payload = {
            'type': 'message_deleted',
            'id': message_id_value,
            'sender_id': str(request.user.pk),
        }
    else:
        return JsonResponse(
            {'error': 'Noma’lum amal.'},
            status=400,
        )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{conversation_id.hex}',
        {'type': payload['type'], 'data': payload},
    )
    return JsonResponse(payload)


@login_required
@require_GET
def share_targets_view(request):
    query = request.GET.get('q', '').strip()
    if query:
        # Explain: panel ichidagi qidiruv — barcha foydalanuvchilar orasidan izlaymiz
        users = (
            CustomUser.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
            .exclude(pk=request.user.pk)
            .prefetch_related('socialaccount_set')
            .order_by('username')[:30]
        )
        searched = True
    else:
        # Explain: qidiruv bo’sh bo’lsa — faqat obuna bo’lgan userlar ro’yxati
        users = (
            request.user.following.all()
            .prefetch_related('socialaccount_set')
            .order_by('username')
        )
        searched = False
    users = list(users)
    following_ids = set(request.user.following.values_list('pk', flat=True))
    html = ''.join(
        render_to_string(
            'partials/share_user.html',
            {
                'target_user': user,
                'is_following': user.pk in following_ids,
            },
            request=request,
        )
        for user in users
    )
    return JsonResponse({
        'html': html,
        'count': len(users),
        'searched': searched,
    })


def _build_shared_post_payload(post, message, sender, conversation):
    return {
        'type': 'message',
        'id': str(message.pk),
        'body': message.body,
        'attachment_type': message.attachment_type,
        'media_url': '',
        'sender': sender.username,
        'sender_id': str(sender.pk),
        'sender_avatar': sender.avatar_url,
        'profile_url': reverse('user_profile', args=[sender.username]),
        'created_at': message.created_at.isoformat(),
        'shared_post': {
            'id': str(post.pk),
            'title': post.title or '',
            'desc': (post.desc or '')[:120],
            'author_username': post.author.username,
            'image_url': post.img.url if post.img else '',
            'url': f"{reverse('home')}#post-{post.pk}",
        },
    }


@login_required
@require_POST
def share_post_view(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author'),
        pk=post_id,
    )
    user_ids = request.POST.getlist('user_ids')
    caption = (request.POST.get('body') or '').strip()[:2000]
    if not user_ids:
        return JsonResponse(
            {'error': 'Kamida bitta foydalanuvchini tanlang.'},
            status=400,
        )
    targets = (
        CustomUser.objects.filter(pk__in=user_ids)
        .exclude(pk=request.user.pk)
        .prefetch_related('socialaccount_set')
    )
    channel_layer = get_channel_layer()
    sender = request.user
    shared_count = 0
    for target in targets:
        conversation, _ = Conversation.get_or_create_direct(sender, target)
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            body=caption,
            attachment_type=Message.SHARE,
            shared_post=post,
        )
        Conversation.objects.filter(pk=conversation.pk).update(
            updated_at=timezone.now(),
        )
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation.pk.hex}',
            {
                'type': 'chat_message',
                'data': _build_shared_post_payload(post, message, sender, conversation),
            },
        )
        shared_count += 1
    return JsonResponse({
        'count': shared_count,
        'message': 'Post ulashildi.',
    })



@login_required
@require_GET
def chat_media_view(request, message_id):
    message = get_object_or_404(
        Message.objects.filter(
            Q(conversation__member_one=request.user)
            | Q(conversation__member_two=request.user),
            media__gt='',
        ),
        pk=message_id,
    )
    content_type = {
        'image': {
            '.gif': 'image/gif',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
        },
        'video': {
            '.mov': 'video/quicktime',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
        },
        'audio': {
            '.m4a': 'audio/mp4',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.wav': 'audio/wav',
            '.webm': 'audio/webm',
        },
    }.get(message.attachment_type, {}).get(
        Path(message.media.name).suffix.lower(),
        'application/octet-stream',
    )
    response = FileResponse(
        message.media.open('rb'),
        content_type=content_type,
    )
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response