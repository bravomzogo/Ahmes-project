# Generated by Django 5.2.3 on 2025-07-28 06:37

import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_student_profile_picture_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailverification',
            name='activation_code_expires',
            field=models.DateTimeField(default=datetime.datetime(2025, 7, 29, 6, 37, 4, 133957, tzinfo=datetime.timezone.utc)),
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('description', models.TextField(blank=True)),
                ('level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='main.level')),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(choices=[('1', 'First Term'), ('2', 'Second Term'), ('3', 'Third Term')], max_length=1)),
                ('academic_year', models.CharField(max_length=20)),
                ('exam_score', models.DecimalField(decimal_places=2, max_digits=5)),
                ('test_score', models.DecimalField(decimal_places=2, max_digits=5)),
                ('assignment_score', models.DecimalField(decimal_places=2, max_digits=5)),
                ('total_score', models.DecimalField(decimal_places=2, editable=False, max_digits=5)),
                ('grade', models.CharField(editable=False, max_length=2)),
                ('remark', models.CharField(editable=False, max_length=100)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('date_approved', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_results', to=settings.AUTH_USER_MODEL)),
                ('school_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.schoolclass')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='main.student')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results_given', to='main.staffmember')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.subject')),
            ],
            options={
                'unique_together': {('student', 'subject', 'term', 'academic_year')},
            },
        ),
    ]
