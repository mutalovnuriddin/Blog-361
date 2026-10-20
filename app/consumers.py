from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import Conversation, CustomUser, Message


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.notification_group = f'notifications_{self.user.pk.hex}'
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'notification_group'):
            await self.channel_layer.group_discard(
                self.notification_group,
                self.channel_name,
            )

    async def notification_event(self, event):
        await self.send_json(event['data'])


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation = await self.get_conversation()
        if self.conversation is None:
            await self.close(code=4403)
            return

        self.chat_group = f'chat_{self.conversation_id.hex}'
        self.user_group = f'user_{self.user.pk.hex}'
        self.peer_group = f'user_{self.peer_id.hex}'

        await self.channel_layer.group_add(self.chat_group, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        online_count = await self.add_presence_connection(self.user.pk)
        await self.send_json({
            'type': 'presence',
            'username': self.peer_username,
            'online': await self.is_online(self.peer_id),
        })
        if online_count == 1:
            await self.channel_layer.group_send(
                self.peer_group,
                {
                    'type': 'presence_update',
                    'username': self.user.username,
                    'online': True,
                },
            )

    async def disconnect(self, close_code):
        if not hasattr(self, 'chat_group'):
            return
        await self.channel_layer.group_discard(self.chat_group, self.channel_name)
        await self.channel_layer.group_discard(self.user_group, self.channel_name)
        remaining_connections = await self.remove_presence_connection(self.user.pk)
        if remaining_connections == 0:
            await self.channel_layer.group_send(
                self.peer_group,
                {
                    'type': 'presence_update',
                    'username': self.user.username,
                    'online': False,
                },
            )

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.send_json({
                'type': 'error',
                'message': 'Chat xabari noto‘g‘ri formatda.',
            })
            return

        event_type = content.get('type')
        if event_type == 'heartbeat':
            await self.refresh_presence(self.user.pk)
            return

        if event_type == 'typing':
            is_typing = content.get('is_typing')
            if not isinstance(is_typing, bool):
                return
            await self.channel_layer.group_send(
                self.chat_group,
                {
                    'type': 'typing_update',
                    'username': self.user.username,
                    'is_typing': is_typing,
                    'sender_channel': self.channel_name,
                },
            )
            return

        if event_type != 'message':
            await self.send_json({
                'type': 'error',
                'message': 'Noma’lum xabar turi.',
            })
            return

        body = content.get('body')
        if not isinstance(body, str) or not body.strip():
            await self.send_json({
                'type': 'error',
                'message': 'Xabar matni bo‘sh bo‘lmasligi kerak.',
            })
            return
        if len(body) > 2000:
            await self.send_json({
                'type': 'error',
                'message': 'Xabar 2000 belgidan oshmasligi kerak.',
            })
            return

        message_data = await self.save_message(body.strip())
        await self.channel_layer.group_send(
            self.chat_group,
            {'type': 'chat_message', 'data': message_data},
        )

    async def chat_message(self, event):
        message_data = event['data']
        if message_data['sender_id'] != str(self.user.pk):
            await self.mark_message_read(message_data['id'])
        await self.send_json(event['data'])

    async def message_updated(self, event):
        await self.send_json(event['data'])

    async def message_deleted(self, event):
        await self.send_json(event['data'])

    async def typing_update(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send_json({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing'],
        })

    async def presence_update(self, event):
        await self.send_json({
            'type': 'presence',
            'username': event['username'],
            'online': event['online'],
        })

    @database_sync_to_async
    def get_conversation(self):
        conversation = (
            Conversation.objects.select_related('member_one', 'member_two')
            .filter(pk=self.conversation_id)
            .first()
        )
        if conversation is None or self.user.pk not in (
            conversation.member_one_id,
            conversation.member_two_id,
        ):
            return None

        peer = conversation.other_member(self.user)
        self.peer_id = peer.pk
        self.peer_username = peer.username
        return conversation

    @database_sync_to_async
    def save_message(self, body):
        with transaction.atomic():
            conversation = Conversation.objects.select_for_update().get(
                pk=self.conversation_id,
            )
            message = Message.objects.create(
                conversation=conversation,
                sender_id=self.user.pk,
                body=body,
            )
            Conversation.objects.filter(pk=conversation.pk).update(
                updated_at=timezone.now(),
            )
        sender = (
            CustomUser.objects.prefetch_related('socialaccount_set')
            .get(pk=self.user.pk)
        )
        return {
            'type': 'message',
            'id': str(message.pk),
            'body': message.body,
            'attachment_type': message.attachment_type,
            'media_url': reverse('chat_media', args=[message.pk]) if message.media else '',
            'sender': sender.username,
            'sender_id': str(sender.pk),
            'sender_avatar': sender.avatar_url,
            'profile_url': reverse('user_profile', args=[sender.username]),
            'created_at': message.created_at.isoformat(),
        }

    @database_sync_to_async
    def mark_message_read(self, message_id):
        Message.objects.filter(
            pk=message_id,
            conversation_id=self.conversation_id,
            read_at__isnull=True,
        ).exclude(sender_id=self.user.pk).update(read_at=timezone.now())

    @database_sync_to_async
    def is_online(self, user_id):
        return bool(cache.get(f'chat_presence_{user_id}', 0))

    @database_sync_to_async
    def add_presence_connection(self, user_id):
        key = f'chat_presence_{user_id}'
        cache.add(key, 0, timeout=90)
        return cache.incr(key)

    @database_sync_to_async
    def remove_presence_connection(self, user_id):
        key = f'chat_presence_{user_id}'
        try:
            remaining = cache.decr(key)
        except ValueError:
            return 0
        if remaining <= 0:
            cache.delete(key)
            return 0
        cache.touch(key, timeout=90)
        return remaining

    @database_sync_to_async
    def refresh_presence(self, user_id):
        key = f'chat_presence_{user_id}'
        if cache.get(key):
            cache.touch(key, timeout=90)
