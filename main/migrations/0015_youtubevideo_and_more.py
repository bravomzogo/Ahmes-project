# Generated by Django 5.2.3 on 2025-07-23 13:14

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_alter_emailverification_activation_code_expires_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='YouTubeVideo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('video_id', models.CharField(max_length=20, unique=True)),
                ('published_at', models.DateTimeField()),
                ('thumbnail_url', models.URLField(max_length=500)),
                ('duration', models.CharField(blank=True, max_length=20)),
                ('is_featured', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'YouTube Video',
                'verbose_name_plural': 'YouTube Videos',
                'ordering': ['-published_at'],
            },
        ),
        migrations.AlterField(
            model_name='emailverification',
            name='activation_code_expires',
            field=models.DateTimeField(default=datetime.datetime(2025, 7, 24, 13, 14, 43, 917306, tzinfo=datetime.timezone.utc)),
        ),
    ]
