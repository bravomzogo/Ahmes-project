from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import secrets
from cloudinary.models import CloudinaryField
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    is_staff_member = models.BooleanField(default=False)
    last_activity = models.DateTimeField(null=True, blank=True)
    
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
        swappable = 'AUTH_USER_MODEL'
        db_table = 'auth_user'

    def __str__(self):
        return self.username
    
    @property
    def is_online(self):
        if self.last_activity:
            return (timezone.now() - self.last_activity) < timedelta(minutes=5)
        return False
 
class Campus(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    description = models.TextField()
    image = CloudinaryField('campuses', folder="school/campuses", 
                          transformation={'quality': 'auto:good'})
    
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
        null=True,
        blank=True
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
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
        null=True,
        blank=True
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
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
    image = CloudinaryField('staff', folder="school/staff",
                          transformation={'quality': 'auto:good'})
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
    image = CloudinaryField('news', folder="school/news",
                          transformation={'quality': 'auto:good'})
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

class Gallery(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    image = CloudinaryField('gallery/images', folder="school/gallery/images", 
                          transformation={'quality': 'auto:good'}, 
                          blank=True, null=True)
    video = CloudinaryField('gallery/videos', folder="school/gallery/videos", 
                           resource_type="video", 
                           transformation={'quality': 'auto:good'},
                           blank=True, null=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='gallery_items'
    )
    published_date = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_date']
        verbose_name = 'Gallery Item'
        verbose_name_plural = 'Gallery Items'

class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    activation_code_expires = models.DateTimeField(default=timezone.now() + timedelta(hours=24))

    def __str__(self):
        return f"Verification for {self.user.email}"

    def generate_new_code(self):
        self.code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        self.created_at = timezone.now()
        self.save()
        return self.code
    
    @classmethod
    def create_for_user(cls, user):
        code = str(secrets.randbelow(900000) + 100000)
        return cls.objects.create(
            user=user,
            code=code
        )

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation between {', '.join([user.username for user in self.participants.all()])}"

    def get_other_user(self, current_user):
        return self.participants.exclude(id=current_user.id).first()

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    file = models.FileField(
        upload_to='chat_files/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 
            'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'mp3', 'mp4'
        ])]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username}" 