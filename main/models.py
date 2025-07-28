from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import secrets
from cloudinary.models import CloudinaryField
from django.core.validators import FileExtensionValidator
from django.templatetags.static import static

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
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    profile_picture = CloudinaryField(
        'students/profile_pictures',
        folder="school/students/profile_pictures",
        transformation={'quality': 'auto:good', 'width': 300, 'height': 300, 'crop': 'fill'},
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.admission_number}"

    def save(self, *args, **kwargs):
        if not self.username:
            # Generate username if not provided (e.g., firstname.lastname)
            self.username = f"{self.first_name.lower()}.{self.last_name.lower()}"
            counter = 1
            while Student.objects.filter(username=self.username).exists():
                self.username = f"{self.first_name.lower()}.{self.last_name.lower()}{counter}"
                counter += 1
        
        # Create/update user account if password is provided
        if self.password and not self.user:
            user = User.objects.create_user(
                username=self.username,
                password=self.password,
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.parent_email
            )
            self.user = user
        elif self.password and self.user:
            self.user.set_password(self.password)
            self.user.save()
        
        super().save(*args, **kwargs)

    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return static('main/images/default-profile.png')

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
    office_number = models.CharField(max_length=20, blank=True)
    office_location = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=200)
    campus = models.ForeignKey(
        Campus,
        on_delete=models.CASCADE,
        related_name='staff_members'
    )
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    joined_date = models.DateField()
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
    conversation = models.ForeignKey('Conversation', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    file = CloudinaryField(
        folder='chat_attachments/',
        null=True,
        blank=True,
        resource_type='auto',
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 
            'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'mp3', 'mp4', 'mov', 'avi'
        ])]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username}"

    @property
    def file_url(self):
        if self.file:
            return self.file.url
        return None

    @property
    def file_name(self):
        if self.file:
            return self.file.public_id.split('/')[-1]
        return None

    @property
    def is_image(self):
        if self.file:
            return self.file.resource_type == 'image'
        return False

    @property
    def is_video(self):
        if self.file:
            return self.file.resource_type == 'video'
        return False
    



# Add this to your models.py
class YouTubeVideo(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_id = models.CharField(max_length=20, unique=True)
    published_at = models.DateTimeField()
    thumbnail_url = models.URLField(max_length=500)
    duration = models.CharField(max_length=20, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'YouTube Video'
        verbose_name_plural = 'YouTube Videos'


class SchoolClass(models.Model):
    name = models.CharField(max_length=100)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    teacher = models.ForeignKey(StaffMember, on_delete=models.CASCADE)
    students = models.ManyToManyField(Student)
    academic_year = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.level.name} ({self.academic_year})"

    @property
    def student_count(self):
        return self.students.count()
    


class CourseCatalog(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='academic/catalogs/')
    academic_year = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.academic_year})"

class AcademicCalendar(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='academic/calendars/')
    academic_year = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.academic_year})"

class AcademicAnnouncement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date = models.DateField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title



class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='subjects')
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Result(models.Model):
    TERM_CHOICES = [
        ('1', 'First Term'),
        ('2', 'Second Term'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    term = models.CharField(max_length=1, choices=TERM_CHOICES)
    academic_year = models.CharField(max_length=20)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2)
    test_score = models.DecimalField(max_digits=5, decimal_places=2)
    assignment_score = models.DecimalField(max_digits=5, decimal_places=2)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    grade = models.CharField(max_length=2, editable=False)
    remark = models.CharField(max_length=100, editable=False)
    teacher = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='results_given')
    date_created = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_results')
    date_approved = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'subject', 'term', 'academic_year')
    
    class Result(models.Model):
     TERM_CHOICES = [
        ('1', 'First Term'),
        ('2', 'Second Term'),
        ('3', 'Third Term'),
     ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    school_class = models.ForeignKey('SchoolClass', on_delete=models.CASCADE)
    term = models.CharField(max_length=1, choices=TERM_CHOICES)
    academic_year = models.CharField(max_length=20)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2)
    test_score = models.DecimalField(max_digits=5, decimal_places=2)
    assignment_score = models.DecimalField(max_digits=5, decimal_places=2)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    grade = models.CharField(max_length=2, editable=False)
    remark = models.CharField(max_length=100, editable=False)
    teacher = models.ForeignKey('StaffMember', on_delete=models.CASCADE, related_name='results_given')
    date_created = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_results')
    date_approved = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('student', 'subject', 'term', 'academic_year')
    
    def save(self, *args, **kwargs):
        # Calculate total score
        self.total_score = (
            self.exam_score * Decimal('0.6') +
            self.test_score * Decimal('0.2') +
            self.assignment_score * Decimal('0.2')
        )
        
        # Determine grade and remark
        if self.total_score >= Decimal('75'):
            self.grade = 'A'
            self.remark = 'Excellent'
        elif self.total_score >= Decimal('65'):
            self.grade = 'B'
            self.remark = 'Very Good'
        elif self.total_score >= Decimal('55'):
            self.grade = 'C'
            self.remark = 'Good'
        elif self.total_score >= Decimal('45'):
            self.grade = 'D'
            self.remark = 'Pass'
        else:
            self.grade = 'F'
            self.remark = 'Fail'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.subject} ({self.term})"