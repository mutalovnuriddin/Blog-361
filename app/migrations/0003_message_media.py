from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_conversation_message_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='body',
            field=models.CharField(blank=True, max_length=2000),
        ),
        migrations.AddField(
            model_name='message',
            name='attachment_type',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='message',
            name='media',
            field=models.FileField(blank=True, upload_to='chat/'),
        ),
    ]
