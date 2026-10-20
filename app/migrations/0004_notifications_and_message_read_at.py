import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models import F
import django.db.models.deletion


def mark_existing_messages_read(apps, schema_editor):
    message_model = apps.get_model('app', 'Message')
    message_model.objects.filter(read_at__isnull=True).update(
        read_at=F('created_at'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_message_media'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'notification_type',
                    models.CharField(
                        choices=[
                            ('like', 'Like'),
                            ('comment', 'Izoh'),
                            ('follow', 'Obuna'),
                        ],
                        max_length=10,
                    ),
                ),
                ('is_read', models.BooleanField(default=False)),
                (
                    'actor',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='sent_notifications',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'comment',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='notifications',
                        to='app.comment',
                    ),
                ),
                (
                    'post',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='notifications',
                        to='app.post',
                    ),
                ),
                (
                    'recipient',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notifications',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['recipient', 'is_read', '-created_at'],
                name='notif_rec_read_created_idx',
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            mark_existing_messages_read,
            migrations.RunPython.noop,
        ),
    ]
