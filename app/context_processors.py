from django.db.models import Q

from .models import Message, Notification


def navigation_counts(request):
    if not request.user.is_authenticated:
        return {
            'unread_notification_count': 0,
            'unread_chat_count': 0,
        }

    user_messages = Message.objects.filter(
        Q(conversation__member_one=request.user)
        | Q(conversation__member_two=request.user),
        read_at__isnull=True,
    ).exclude(sender=request.user)
    return {
        'unread_notification_count': Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count(),
        'unread_chat_count': user_messages.count(),
    }
