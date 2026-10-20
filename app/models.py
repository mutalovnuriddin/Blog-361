import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomUser(AbstractUser, BaseModel):
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Avatar")
    bio = models.TextField(blank=True, null=True, verbose_name="Biografiya")
    phone_number = models.CharField(max_length=13, blank=True, null=True)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url

        for account in self.socialaccount_set.all():
            if account.provider == 'google':
                return account.extra_data.get('picture')
        return None

    def __str__(self):
        return self.username


class Post(BaseModel):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255, blank=True, null=True)
    desc = models.TextField(blank=True, null=True)
    img = models.ImageField(upload_to='posts/images/', blank=True, null=True)
    video = models.FileField(upload_to='posts/videos/', blank=True, null=True)
    likes = models.ManyToManyField(CustomUser, related_name='liked_posts', blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return f"{self.author.username} - {self.title or self.desc[:20]}"


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} -> {self.post.id}: {self.text[:20]}"


class Notification(BaseModel):
    LIKE = 'like'
    COMMENT = 'comment'
    FOLLOW = 'follow'
    TYPE_CHOICES = [
        (LIKE, 'Like'),
        (COMMENT, 'Izoh'),
        (FOLLOW, 'Obuna'),
    ]

    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
    )
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='notifications',
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='notifications',
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['recipient', 'is_read', '-created_at'],
                name='notif_rec_read_created_idx',
            ),
        ]

    def __str__(self):
        return f"{self.actor.username} → {self.recipient.username}: {self.notification_type}"


class Conversation(BaseModel):
    member_one = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='conversations_as_member_one',
    )
    member_two = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='conversations_as_member_two',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['member_one', 'member_two'],
                name='unique_direct_conversation',
            ),
            models.CheckConstraint(
                condition=~models.Q(member_one=models.F('member_two')),
                name='conversation_members_must_differ',
            ),
        ]
        ordering = ['-updated_at']

    @classmethod
    def get_or_create_direct(cls, user, other_user):
        members = sorted((user, other_user), key=lambda member: str(member.pk))
        return cls.objects.get_or_create(
            member_one=members[0],
            member_two=members[1],
        )

    def other_member(self, user):
        if user.pk == self.member_one_id:
            return self.member_two
        if user.pk == self.member_two_id:
            return self.member_one
        raise ValueError('User is not a member of this conversation.')

    def __str__(self):
        return f"{self.member_one.username} ↔ {self.member_two.username}"


class Message(BaseModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    body = models.CharField(max_length=2000, blank=True)
    shared_post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='shared_messages',
        verbose_name="Ulashilgan post",
    )
    attachment_type = models.CharField(max_length=10, blank=True)
    media = models.FileField(upload_to='chat/', blank=True)
    read_at = models.DateTimeField(blank=True, null=True)

    SHARE = 'share'

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.body[:40]}"