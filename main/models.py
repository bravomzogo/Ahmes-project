from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    is_staff_member = models.BooleanField(default=False)
    
    # Updated ManyToManyField relationships with proper related_name
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",
        related_query_name="user",
    )

    class Meta:
        # Ensure this model is used as the custom user model
        swappable = 'AUTH_USER_MODEL'
        db_table = 'auth_user'  # Optional: keeps the same table name as default User

    def __str__(self):
        return self.username

class Campus(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='campuses/')
    
    def __str__(self):
        return self.name

class Level(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.name

class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        null=True,  # Make optional if needed
        blank=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    admission_number = models.CharField(max_length=20, unique=True)
    campus = models.ForeignKey(
        Campus,
        on_delete=models.CASCADE,
        related_name='students'
    )
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name='students'
    )
    admission_date = models.DateField()
    parent_name = models.CharField(max_length=200)
    parent_phone = models.CharField(max_length=20)
    parent_email = models.EmailField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.admission_number}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

class StaffMember(models.Model):
    POSITION_CHOICES = [
        ('Teacher', 'Teacher'),
        ('Administrator', 'Administrator'),
        ('Support', 'Support Staff'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile',
        null=True,  # Make optional if needed
        blank=True
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    qualification = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200)
    campus = models.ForeignKey(
        Campus,
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    joined_date = models.DateField()
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to='staff/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'

class News(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='news/')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='news_posts'
    )
    published_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_date']
        verbose_name = 'News'
        verbose_name_plural = 'News'

class Comment(models.Model):
    content = models.TextField()
    author_name = models.CharField(max_length=100, blank=True)
    author_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Comment by {self.author_name or 'Anonymous'} on {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'