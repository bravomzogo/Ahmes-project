# Generated by Django 5.2.3 on 2025-07-24 16:32

import cloudinary.models
import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_student_password_student_username_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='profile_picture',
            field=cloudinary.models.CloudinaryField(blank=True, max_length=255, null=True, verbose_name='students/profile_pictures'),
        ),
        migrations.AlterField(
            model_name='emailverification',
            name='activation_code_expires',
            field=models.DateTimeField(default=datetime.datetime(2025, 7, 25, 16, 32, 21, 895559, tzinfo=datetime.timezone.utc)),
        ),
    ]
