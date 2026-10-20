import tempfile
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from allauth.socialaccount.models import SocialAccount
from config.asgi import application
from .models import (
    Comment,
    Conversation,
    CustomUser,
    Message,
    Notification,
    Post,
)


class ProfileSettingsTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='north-user',
            email='north@example.com',
            password='CurrentPass987!',
        )
        self.client.force_login(self.user)

    def test_profile_settings_page_only_shows_profile_form(self):
        response = self.client.get(reverse('profile_edit'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profil ma’lumotlari')
        self.assertContains(response, 'Parol va xavfsizlik')
        self.assertNotContains(response, 'Joriy parol')

    def test_password_settings_page_only_shows_password_form(self):
        response = self.client.get(reverse('password_change'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Joriy parol')
        self.assertContains(response, 'Profil ma’lumotlari')
        self.assertNotContains(response, 'Telefon raqam')

    def test_profile_details_can_be_updated_separately(self):
        response = self.client.post(
            reverse('profile_edit'),
            {
                'username': 'updated-user',
                'email': 'updated@example.com',
                'phone_number': '+998901234567',
                'bio': 'Yangi biografiya',
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'updated-user')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.phone_number, '+998901234567')
        self.assertEqual(self.user.bio, 'Yangi biografiya')

    def test_password_can_be_changed_and_session_stays_authenticated(self):
        response = self.client.post(
            reverse('password_change'),
            {
                'old_password': 'CurrentPass987!',
                'new_password1': 'NewSecurePass987!',
                'new_password2': 'NewSecurePass987!',
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass987!'))
        self.assertEqual(
            str(self.client.session['_auth_user_id']),
            str(self.user.pk),
        )


class RegistrationTests(TestCase):
    def test_registration_logs_user_in_with_explicit_backend(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'new-member',
                'email': 'new-member@example.com',
                'password1': 'NewMemberSecure987!',
                'password2': 'NewMemberSecure987!',
            },
        )

        self.assertRedirects(response, reverse('home'))
        user = CustomUser.objects.get(username='new-member')
        self.assertEqual(
            self.client.session['_auth_user_backend'],
            'django.contrib.auth.backends.ModelBackend',
        )
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))


class PostAndProfilePageTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='post-author',
            email='author@example.com',
            password='CurrentPass987!',
            bio='Post muallifi haqida',
        )
        self.other_user = CustomUser.objects.create_user(
            username='another-author',
            email='private@example.com',
            password='CurrentPass987!',
        )
        self.client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.other_user,
            title='Birinchi post',
            desc='Post matni',
        )
        self.own_post = Post.objects.create(
            author=self.user,
            title='Faqat mening postim',
            desc='Boshqa foydalanuvchiga ko‘rinmasin',
        )

    def test_home_shows_posts_and_links_to_a_separate_author_profile(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Birinchi post')
        self.assertContains(
            response,
            reverse('user_profile', args=[self.other_user.username]),
        )
        self.assertNotContains(response, 'private@example.com')

    def test_home_only_shows_the_post_feed(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Yangi post')
        self.assertNotContains(response, 'Postni ulashish')

    def test_home_does_not_accept_post_creation(self):
        response = self.client.post(
            reverse('home'),
            {'title': 'Yangi post', 'desc': 'Bosh sahifadan ulashildi'},
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(Post.objects.filter(title='Yangi post').exists())

    def test_own_profile_creates_post_for_logged_in_user(self):
        response = self.client.post(
            reverse('profile'),
            {'title': 'Profil post', 'desc': 'Profilimdan ulashildi'},
        )

        self.assertRedirects(response, reverse('profile'))
        post = Post.objects.get(title='Profil post')
        self.assertEqual(post.author, self.user)

    def test_other_users_profile_does_not_allow_post_creation(self):
        response = self.client.post(
            reverse('user_profile', args=[self.other_user.username]),
            {'title': 'Begona profilga post', 'desc': 'Ruxsat berilmasin'},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Post.objects.filter(title='Begona profilga post').exists())

    def test_profile_page_shows_only_that_users_posts_and_private_contact_only_to_owner(self):
        response = self.client.get(
            reverse('user_profile', args=[self.other_user.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Birinchi post')
        self.assertNotContains(response, 'Faqat mening postim')
        self.assertNotContains(response, 'Post muallifi haqida')
        self.assertNotContains(response, 'private@example.com')

    def test_own_profile_page_is_available_at_profile_url(self):
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)
        # Explain: profil sahifasi endi yangi post qo’shish formasi o’rniga
        # /add/post/ sahifasiga havola ko’rsatadi
        self.assertContains(response, "Post qo'shish")
        self.assertContains(response, reverse('add_post'))

    def test_unknown_profile_returns_not_found(self):
        response = self.client.get(reverse('user_profile', args=['missing-user']))

        self.assertEqual(response.status_code, 404)


class UserSearchTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='searching-user',
            email='searching@example.com',
            password='CurrentPass987!',
        )
        self.match = CustomUser.objects.create_user(
            username='north-member',
            email='member@example.com',
            password='CurrentPass987!',
            first_name='Another',
            last_name='Member',
        )
        self.client.force_login(self.user)

    def test_homepage_has_ajax_user_search(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-user-search')
        self.assertContains(response, reverse('search_users'))

    def test_ajax_search_returns_matching_user_profile_link(self):
        response = self.client.get(
            reverse('search_users'),
            {'q': 'north'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertIn('north-member', response.json()['html'])
        self.assertIn(
            reverse('user_profile', args=[self.match.username]),
            response.json()['html'],
        )
        self.assertNotIn(self.user.username, response.json()['html'])

    def test_ajax_search_ignores_blank_queries(self):
        response = self.client.get(
            reverse('search_users'),
            {'q': '   '},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'html': '', 'count': 0})

    def test_search_requires_authentication(self):
        self.client.logout()

        response = self.client.get(reverse('search_users'), {'q': 'north'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
        self.assertIn('next=', response.url)
        self.assertIn('search', response.url)


class UserConnectionsTests(TestCase):
    def setUp(self):
        self.viewer = CustomUser.objects.create_user(
            username='connections-viewer',
            email='viewer@example.com',
            password='CurrentPass987!',
        )
        self.profile_user = CustomUser.objects.create_user(
            username='connections-profile',
            email='profile@example.com',
            password='CurrentPass987!',
        )
        self.followed_user = CustomUser.objects.create_user(
            username='followed-member',
            email='followed@example.com',
            password='CurrentPass987!',
            first_name='Followed',
            last_name='Member',
        )
        self.follower_user = CustomUser.objects.create_user(
            username='follower-member',
            email='follower@example.com',
            password='CurrentPass987!',
        )
        self.profile_user.following.add(self.followed_user)
        self.follower_user.following.add(self.profile_user)
        self.client.force_login(self.viewer)

    def test_profile_shows_clickable_follower_and_following_counts(self):
        response = self.client.get(
            reverse('user_profile', args=[self.profile_user.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-connections-dialog')
        self.assertContains(
            response,
            reverse(
                'user_connections',
                args=[self.profile_user.username, 'following'],
            ),
        )
        self.assertContains(
            response,
            reverse(
                'user_connections',
                args=[self.profile_user.username, 'followers'],
            ),
        )

    def test_following_endpoint_lists_accounts_the_profile_follows(self):
        response = self.client.get(
            reverse(
                'user_connections',
                args=[self.profile_user.username, 'following'],
            ),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['title'], 'Obuna bo‘lganlar')
        self.assertIn(self.followed_user.username, response.json()['html'])
        self.assertNotIn(self.follower_user.username, response.json()['html'])
        self.assertIn(
            reverse('user_profile', args=[self.followed_user.username]),
            response.json()['html'],
        )

    def test_followers_endpoint_lists_accounts_following_the_profile(self):
        response = self.client.get(
            reverse(
                'user_connections',
                args=[self.profile_user.username, 'followers'],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['title'], 'Obunachilar')
        self.assertIn(self.follower_user.username, response.json()['html'])
        self.assertNotIn(self.followed_user.username, response.json()['html'])

    def test_connection_endpoint_rejects_unknown_list_types(self):
        response = self.client.get(
            reverse(
                'user_connections',
                args=[self.profile_user.username, 'unknown'],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_connection_endpoint_requires_authentication(self):
        self.client.logout()

        response = self.client.get(
            reverse(
                'user_connections',
                args=[self.profile_user.username, 'following'],
            )
        )

        self.assertEqual(response.status_code, 302)


class ChatPageTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='chat-viewer',
            email='chat-viewer@example.com',
            password='CurrentPass987!',
        )
        self.peer = CustomUser.objects.create_user(
            username='chat-peer',
            email='chat-peer@example.com',
            password='CurrentPass987!',
        )
        self.client.force_login(self.user)

    def test_profile_has_chat_button_for_other_users(self):
        response = self.client.get(
            reverse('user_profile', args=[self.peer.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chat')
        self.assertContains(
            response,
            reverse('chat_user', args=[self.peer.username]),
        )

    def test_opening_a_profile_chat_creates_one_persistent_conversation(self):
        response = self.client.get(
            reverse('chat_user', args=[self.peer.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.peer.username)
        self.assertContains(response, 'data-chat-app')
        conversation = Conversation.objects.get()
        self.assertContains(
            response,
            f'data-socket-url="/ws/chat/{conversation.pk}/"',
        )
        self.assertContains(
            response,
            f'data-peer-username="{self.peer.username}"',
        )

        second_response = self.client.get(
            reverse('chat_user', args=[self.peer.username])
        )

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)

        self.client.force_login(self.peer)
        reverse_response = self.client.get(
            reverse('chat_user', args=[self.user.username])
        )

        self.assertEqual(reverse_response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)

    def test_chat_index_shows_empty_state_when_there_are_no_conversations(self):
        response = self.client.get(reverse('chat'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Xabarlaringiz shu yerda')
        self.assertEqual(Conversation.objects.count(), 0)

    def test_chat_page_shows_existing_message_history(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            body='Saqlangan chat xabari',
        )

        response = self.client.get(
            reverse('chat_user', args=[self.peer.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Saqlangan chat xabari')
        self.assertContains(response, self.peer.username)
        self.assertContains(response, 'data-message-action="edit"')
        self.assertContains(response, 'data-message-action="delete"')
        self.assertContains(response, 'data-attachment-preview')
        self.assertContains(response, 'data-attachment-cancel')

        self.client.post(
            reverse('chat_message_action', args=[message.pk]),
            {'action': 'edit', 'body': 'Yangilangan xabar'},
        )
        message.refresh_from_db()
        self.assertEqual(message.body, 'Yangilangan xabar')

        self.client.post(
            reverse('chat_message_action', args=[message.pk]),
            {'action': 'delete'},
        )
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())

    def test_chat_message_edits_and_deletes_are_limited_to_sender(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.peer,
            body='Faqat yuboruvchi o‘zgartiradi',
        )
        endpoint = reverse('chat_message_action', args=[message.pk])

        edit_response = self.client.post(
            endpoint,
            {'action': 'edit', 'body': 'Ruxsatsiz tahrir'},
        )
        delete_response = self.client.post(endpoint, {'action': 'delete'})

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        message.refresh_from_db()
        self.assertEqual(message.body, 'Faqat yuboruvchi o‘zgartiradi')

    def test_chat_message_edit_requires_non_empty_body(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            body='Avvalgi xabar',
        )

        response = self.client.post(
            reverse('chat_message_action', args=[message.pk]),
            {'action': 'edit', 'body': '  '},
        )

        self.assertEqual(response.status_code, 400)
        message.refresh_from_db()
        self.assertEqual(message.body, 'Avvalgi xabar')

    def test_deleting_own_media_message_removes_uploaded_file(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        with tempfile.TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
        ):
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                attachment_type='image',
                media=SimpleUploadedFile(
                    'photo.png',
                    b'image bytes',
                    content_type='image/png',
                ),
            )
            media_name = message.media.name
            storage = message.media.storage
            self.assertTrue(storage.exists(media_name))

            response = self.client.post(
                reverse('chat_message_action', args=[message.pk]),
                {'action': 'delete'},
            )

            self.assertEqual(response.status_code, 200)
            self.assertFalse(storage.exists(media_name))
            self.assertFalse(Message.objects.filter(pk=message.pk).exists())

    def test_chat_sidebar_shows_unread_count_and_opening_marks_messages_read(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        unread_messages = [
            Message.objects.create(
                conversation=conversation,
                sender=self.peer,
                body=f'O‘qilmagan xabar {index}',
            )
            for index in range(3)
        ]
        Message.objects.create(
            conversation=conversation,
            sender=self.user,
            body='Men yuborgan xabar',
        )

        response = self.client.get(reverse('chat'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3 ta o‘qilmagan xabar')
        self.assertContains(response, '>3</span>')

        response = self.client.get(
            reverse('chat_user', args=[self.peer.username]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(
                Message.objects.get(pk=message.pk).read_at is not None
                for message in unread_messages
            )
        )
        self.assertNotContains(response, '3 ta o‘qilmagan xabar')

    def test_chat_members_can_send_audio_attachments(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        upload_url = reverse('chat_upload_media', args=[conversation.pk])

        with tempfile.TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
        ):
            response = self.client.post(
                upload_url,
                {
                    'attachment_type': 'audio',
                    'file': SimpleUploadedFile(
                        'voice.webm',
                        b'voice sample',
                        content_type='audio/webm',
                    ),
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['attachment_type'], 'audio')
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(
            response.json()['media_url'],
            reverse('chat_media', args=[message.pk]),
        )
        self.assertEqual(message.body, '')
        self.assertEqual(message.attachment_type, 'audio')

    def test_chat_media_is_only_available_to_conversation_members(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        with tempfile.TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
        ):
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                attachment_type='audio',
                media=SimpleUploadedFile(
                    'voice.webm',
                    b'voice sample',
                    content_type='audio/webm',
                ),
            )
            media_url = reverse('chat_media', args=[message.pk])
            response = self.client.get(media_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'audio/webm')
            self.assertEqual(response['Cache-Control'], 'private, no-store')

            outsider = CustomUser.objects.create_user(
                username='media-outsider',
                email='media-outsider@example.com',
                password='CurrentPass987!',
            )
            self.client.force_login(outsider)
            self.assertEqual(self.client.get(media_url).status_code, 404)

    def test_chat_upload_rejects_unsupported_file_types(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)

        response = self.client.post(
            reverse('chat_upload_media', args=[conversation.pk]),
            {
                'attachment_type': 'image',
                'file': SimpleUploadedFile(
                    'not-an-image.exe',
                    b'not an image',
                    content_type='application/octet-stream',
                ),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_non_members_cannot_upload_chat_attachments(self):
        conversation, _ = Conversation.get_or_create_direct(self.user, self.peer)
        self.client.force_login(CustomUser.objects.create_user(
            username='chat-outsider',
            email='chat-outsider@example.com',
            password='CurrentPass987!',
        ))

        response = self.client.post(
            reverse('chat_upload_media', args=[conversation.pk]),
            {
                'attachment_type': 'audio',
                'file': SimpleUploadedFile(
                    'voice.webm',
                    b'voice sample',
                    content_type='audio/webm',
                ),
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Message.objects.count(), 0)

    def test_users_cannot_open_a_chat_with_themselves(self):
        response = self.client.get(
            reverse('chat_user', args=[self.user.username])
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_chat_pages_require_authentication(self):
        self.client.logout()

        response = self.client.get(reverse('chat'))

        self.assertEqual(response.status_code, 302)


@override_settings(ALLOWED_HOSTS=['testserver'])
class ChatWebSocketTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.sender = CustomUser.objects.create_user(
            username='socket-sender',
            email='socket-sender@example.com',
            password='CurrentPass987!',
        )
        self.receiver = CustomUser.objects.create_user(
            username='socket-receiver',
            email='socket-receiver@example.com',
            password='CurrentPass987!',
        )
        self.stranger = CustomUser.objects.create_user(
            username='socket-stranger',
            email='socket-stranger@example.com',
            password='CurrentPass987!',
        )
        self.conversation, _ = Conversation.get_or_create_direct(
            self.sender,
            self.receiver,
        )
        self.session_cookies = {}
        for user in (self.sender, self.receiver, self.stranger):
            client = self.client_class()
            client.force_login(user)
            self.session_cookies[user.pk] = client.cookies[
                settings.SESSION_COOKIE_NAME
            ].value

    def _communicator_for(self, user, conversation=None):
        conversation_id = conversation.pk if conversation else self.conversation.pk
        path = f'/ws/chat/{conversation_id}/'
        return WebsocketCommunicator(
            application,
            path,
            headers=[
                (b'origin', b'http://testserver'),
                (
                    b'cookie',
                    (
                        f'{settings.SESSION_COOKIE_NAME}='
                        f'{self.session_cookies[user.pk]}'
                    ).encode(),
                ),
            ],
        )

    def test_chat_members_exchange_messages_and_typing_events_over_websocket(self):
        async_to_sync(self._exchange_chat_events)()

        self.assertEqual(
            Message.objects.filter(conversation=self.conversation).count(),
            1,
        )
        self.assertEqual(
            Message.objects.get(conversation=self.conversation).body,
            'WebSocket orqali salom 💚',
        )
        self.assertIsNotNone(
            Message.objects.get(conversation=self.conversation).read_at,
        )

    async def _exchange_chat_events(self):
        sender_socket = self._communicator_for(self.sender)
        receiver_socket = self._communicator_for(self.receiver)
        sender_connected, _ = await sender_socket.connect()
        self.assertTrue(sender_connected)
        await sender_socket.receive_json_from()

        receiver_connected, _ = await receiver_socket.connect()
        self.assertTrue(receiver_connected)
        await sender_socket.receive_json_from()
        receiver_presence = await receiver_socket.receive_json_from()
        self.assertEqual(receiver_presence['type'], 'presence')
        self.assertTrue(receiver_presence['online'])

        await sender_socket.send_json_to({
            'type': 'typing',
            'is_typing': True,
        })
        typing_event = await receiver_socket.receive_json_from()
        self.assertEqual(typing_event, {
            'type': 'typing',
            'username': self.sender.username,
            'is_typing': True,
        })

        await sender_socket.send_json_to({
            'type': 'message',
            'body': 'WebSocket orqali salom 💚',
        })
        sender_message = await sender_socket.receive_json_from()
        receiver_message = await receiver_socket.receive_json_from()
        self.assertEqual(sender_message['body'], 'WebSocket orqali salom 💚')
        self.assertEqual(receiver_message['body'], 'WebSocket orqali salom 💚')
        self.assertEqual(sender_message['sender'], self.sender.username)

        await sender_socket.disconnect()
        await receiver_socket.disconnect()

    def test_non_member_is_denied_websocket_access(self):
        async_to_sync(self._deny_non_member)()

    async def _deny_non_member(self):
        stranger_socket = self._communicator_for(self.stranger)
        connected, close_code = await stranger_socket.connect()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)


@override_settings(ALLOWED_HOSTS=['testserver'])
class NotificationWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.actor = CustomUser.objects.create_user(
            username='notification-actor',
            email='notification-actor@example.com',
            password='CurrentPass987!',
        )
        self.recipient = CustomUser.objects.create_user(
            username='notification-recipient',
            email='notification-recipient@example.com',
            password='CurrentPass987!',
        )
        self.post = Post.objects.create(
            author=self.recipient,
            desc='Jonli bildirishnoma posti',
        )
        client = self.client_class()
        client.force_login(self.actor)
        self.client = client
        recipient_client = self.client_class()
        recipient_client.force_login(self.recipient)
        self.recipient_cookie = recipient_client.cookies[
            settings.SESSION_COOKIE_NAME
        ].value

    def test_like_notification_is_delivered_without_page_reload(self):
        async_to_sync(self._like_and_receive_notification)()

    async def _like_and_receive_notification(self):
        communicator = WebsocketCommunicator(
            application,
            '/ws/notifications/',
            headers=[
                (b'origin', b'http://testserver'),
                (
                    b'cookie',
                    (
                        f'{settings.SESSION_COOKIE_NAME}={self.recipient_cookie}'
                    ).encode(),
                ),
            ],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        response = await sync_to_async(self.client.post, thread_sensitive=True)(
            reverse('like_post', args=[self.post.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

        event = await communicator.receive_json_from()
        self.assertEqual(event['type'], 'notification')
        self.assertEqual(event['unread_count'], 1)
        self.assertEqual(event['actor_username'], self.actor.username)
        self.assertIn(self.post.desc, event['html'])

        await communicator.disconnect()


class SocialInteractionTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='social-user',
            email='social@example.com',
            password='CurrentPass987!',
        )
        self.author = CustomUser.objects.create_user(
            username='social-author',
            email='author@example.com',
            password='CurrentPass987!',
        )
        self.post = Post.objects.create(author=self.author, desc='Post uchun matn')
        self.client.force_login(self.user)

    def test_feed_renders_post_actions_and_google_avatar(self):
        SocialAccount.objects.create(
            user=self.author,
            provider='google',
            uid='google-social-author',
            extra_data={'picture': 'https://example.com/google-avatar.jpg'},
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://example.com/google-avatar.jpg')
        self.assertContains(response, reverse('like_post', args=[self.post.pk]))
        self.assertContains(response, reverse('add_comment', args=[self.post.pk]))

    def test_like_can_be_added_and_removed(self):
        response = self.client.post(
            reverse('like_post', args=[self.post.pk]),
            HTTP_REFERER='/',
        )
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(self.post.likes.filter(pk=self.user.pk).exists())

        self.client.post(reverse('like_post', args=[self.post.pk]), HTTP_REFERER='/')
        self.assertFalse(self.post.likes.filter(pk=self.user.pk).exists())

    def test_like_and_comment_create_post_notifications_with_post_context(self):
        self.post.title = 'Notification uchun post'
        self.post.save(update_fields=['title'])

        self.client.post(reverse('like_post', args=[self.post.pk]))
        comment_response = self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'text': 'Ajoyib post!'},
        )

        self.assertEqual(comment_response.status_code, 302)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.author,
                actor=self.user,
                post=self.post,
            ).count(),
            2,
        )
        self.client.force_login(self.author)
        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertContains(response, 'Notification uchun post')
        self.assertContains(response, 'Ajoyib post!')
        self.assertContains(
            response,
            reverse(
                'notification_open',
                args=[Notification.objects.first().pk],
            ),
        )

    def test_notifications_are_private_and_can_be_marked_read(self):
        notification = Notification.objects.create(
            recipient=self.author,
            actor=self.user,
            notification_type=Notification.LIKE,
            post=self.post,
        )
        self.client.force_login(self.author)

        response = self.client.get(reverse('notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-unread')
        self.assertContains(response, self.user.username)

        self.client.post(reverse('notifications_read'))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

        notification = Notification.objects.create(
            recipient=self.author,
            actor=self.user,
            notification_type=Notification.COMMENT,
            post=self.post,
        )
        open_response = self.client.post(
            reverse('notification_open', args=[notification.pk]),
        )
        self.assertRedirects(
            open_response,
            reverse('home') + f'#post-{self.post.pk}',
        )
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

        self.client.force_login(
            CustomUser.objects.create_user(
                username='notification-outsider',
                email='notification-outsider@example.com',
                password='CurrentPass987!',
            )
        )
        self.assertEqual(
            self.client.post(
                reverse('notification_open', args=[notification.pk]),
            ).status_code,
            404,
        )

    def test_ajax_like_returns_updated_post_card(self):
        response = self.client.post(
            reverse('like_post', args=[self.post.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['html'].count('like-button is-liked'), 1)
        self.assertTrue(self.post.likes.filter(pk=self.user.pk).exists())

    def test_comment_is_saved_for_authenticated_user(self):
        response = self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'text': 'Ajoyib post!'},
            HTTP_REFERER='/',
        )

        self.assertRedirects(response, reverse('home'))
        comment = Comment.objects.get(post=self.post)
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.text, 'Ajoyib post!')
        self.assertContains(self.client.get(reverse('home')), 'Ajoyib post!')
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.author,
                actor=self.user,
                notification_type=Notification.COMMENT,
                comment=comment,
            ).exists()
        )

    def test_ajax_comment_returns_updated_post_card_without_redirect(self):
        response = self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'text': 'AJAX izohi'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('AJAX izohi', response.json()['html'])
        self.assertEqual(response.json()['html'].count('comment-count">1'), 1)

    def test_ajax_comment_validation_errors_are_returned_to_the_client(self):
        response = self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'text': ''},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('text', response.json()['errors'])
        self.assertFalse(Comment.objects.filter(post=self.post).exists())

    def test_follow_and_unfollow_are_available_from_profile(self):
        profile_url = reverse('user_profile', args=[self.author.username])
        follow_url = reverse('follow_toggle', args=[self.author.pk])

        response = self.client.get(profile_url)
        self.assertContains(response, 'Obuna bo‘lish')

        self.client.post(follow_url, HTTP_REFERER=profile_url)
        self.assertTrue(self.user.following.filter(pk=self.author.pk).exists())
        self.assertContains(self.client.get(profile_url), 'Obunani bekor qilish')

        self.client.post(follow_url, HTTP_REFERER=profile_url)
        self.assertFalse(self.user.following.filter(pk=self.author.pk).exists())
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.author,
                actor=self.user,
                notification_type=Notification.FOLLOW,
            ).count(),
            1,
        )

    def test_ajax_follow_returns_updated_counts(self):
        response = self.client.post(
            reverse('follow_toggle', args=[self.author.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'is_following': True,
            'followers_count': 1,
            'following_count': 0,
        })

    def test_social_action_ignores_external_referer(self):
        response = self.client.post(
            reverse('like_post', args=[self.post.pk]),
            HTTP_REFERER='https://outside.example/',
        )

        self.assertRedirects(response, reverse('home'))

    def test_logout_requires_post_and_ends_the_session(self):
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)

        response = self.client.post(reverse('logout'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))

        # Bosh sahifa endi anonim foydalanuvchini ham qabul qiladi: postlar
        # feedini tizimga kirmasdan ko‘rish mumkin.
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)


class SharePostTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='share-sender',
            email='share-sender@example.com',
            password='CurrentPass987!',
        )
        self.author = CustomUser.objects.create_user(
            username='share-author',
            email='share-author@example.com',
            password='CurrentPass987!',
        )
        self.followed_user = CustomUser.objects.create_user(
            username='followed-friend',
            email='followed@example.com',
            password='CurrentPass987!',
        )
        self.stranger = CustomUser.objects.create_user(
            username='search-stranger',
            email='stranger@example.com',
            password='CurrentPass987!',
        )
        self.user.following.add(self.followed_user)
        self.post = Post.objects.create(
            author=self.author,
            title='Ulashiladigan post',
            desc='Chatga yuboriladi',
        )
        self.client.force_login(self.user)

    def test_share_targets_lists_only_followed_users(self):
        response = self.client.get(reverse('share_targets'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 1)
        self.assertIn(self.followed_user.username, payload['html'])
        self.assertNotIn(self.stranger.username, payload['html'])
        self.assertFalse(payload['searched'])

    def test_share_targets_search_finds_users_outside_following(self):
        response = self.client.get(
            reverse('share_targets'),
            {'q': 'search-stranger'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['searched'])
        self.assertIn(self.stranger.username, payload['html'])
        self.assertNotIn(self.followed_user.username, payload['html'])

    def test_share_targets_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('share_targets'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_share_post_creates_a_message_in_each_chat(self):
        response = self.client.post(
            reverse('share_post', args=[self.post.pk]),
            {
                'user_ids': [str(self.followed_user.pk), str(self.stranger.pk)],
                'body': 'Bu postni ko‘r!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 2)
        self.assertEqual(Message.objects.count(), 2)
        for message in Message.objects.all():
            self.assertEqual(message.sender, self.user)
            self.assertEqual(message.attachment_type, 'share')
            self.assertEqual(message.shared_post, self.post)
            self.assertEqual(message.body, 'Bu postni ko‘r!')

    def test_share_post_without_targets_returns_bad_request(self):
        response = self.client.post(reverse('share_post', args=[self.post.pk]), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_shared_post_appears_in_chat_page(self):
        self.client.post(
            reverse('share_post', args=[self.post.pk]),
            {'user_ids': [str(self.followed_user.pk)]},
        )

        response = self.client.get(
            reverse('chat_user', args=[self.followed_user.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'chat-shared-post')
        self.assertContains(response, 'Ulangan post')
        self.assertContains(response, 'Ulashiladigan post')

        self.client.force_login(self.followed_user)
        peer_response = self.client.get(
            reverse('chat_user', args=[self.user.username])
        )

        self.assertEqual(peer_response.status_code, 200)
        self.assertContains(peer_response, 'Ulangan post')

    def test_chat_list_preview_marks_shared_post(self):
        self.client.post(
            reverse('share_post', args=[self.post.pk]),
            {'user_ids': [str(self.followed_user.pk)]},
        )

        response = self.client.get(reverse('chat'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Post ulashildi')


class AnonymousFeedAccessTests(TestCase):
    """Ommaviy feed: kirishda ko‘rish mumkin, amallar uchun login talab qilinadi."""

    def setUp(self):
        self.author = CustomUser.objects.create_user(
            username='public-author',
            email='public@example.com',
            password='CurrentPass987!',
        )
        self.post = Post.objects.create(
            author=self.author,
            title='Ommaviy post',
            desc='Tizimsiz ham ko‘rinadi.',
        )

    def test_home_feed_is_browsable_without_login(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ommaviy post')

    def test_like_requires_login(self):
        response = self.client.post(reverse('like_post', args=[self.post.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_share_requires_login(self):
        response = self.client.post(
            reverse('share_post', args=[self.post.pk]),
            {'user_ids': [str(self.author.pk)]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_follow_requires_login(self):
        response = self.client.post(reverse('follow_toggle', args=[self.author.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_chat_requires_login(self):
        response = self.client.get(reverse('chat'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_comment_requires_login(self):
        response = self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'text': 'Izoh'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
