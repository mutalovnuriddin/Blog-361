from django.urls import path

from .consumers import ChatConsumer, NotificationConsumer


websocket_urlpatterns = [
    path(
        'ws/notifications/',
        NotificationConsumer.as_asgi(),
        name='notifications_socket',
    ),
    path(
        'ws/chat/<uuid:conversation_id>/',
        ChatConsumer.as_asgi(),
        name='chat_socket',
    ),
]
