# Generated by Django 5.2.3 on 2025-07-24 07:26

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_alter_emailverification_activation_code_expires'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailverification',
            name='activation_code_expires',
            field=models.DateTimeField(default=datetime.datetime(2025, 7, 25, 7, 26, 55, 538343, tzinfo=datetime.timezone.utc)),
        ),
    ]
