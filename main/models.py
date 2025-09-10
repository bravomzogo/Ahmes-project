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
import random
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    is_parent = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_staff_member = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
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




class Parent(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='parent_profile',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    address = models.TextField()
    profile_picture = CloudinaryField(
        'parents/profile_pictures',
        folder="school/parents/profile_pictures",
        transformation={'quality': 'auto:good', 'width': 300, 'height': 300, 'crop': 'fill'},
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return static('main/images/default-profile.png')

    class Meta:
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'




class ParentOTP(models.Model):
    parent = models.ForeignKey('Parent', on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.parent.name} - {self.otp}"
    
    def is_valid(self):
        # OTP valid for 10 minutes
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=10)
    
    @classmethod
    def generate_otp(cls, parent):
        # Delete any existing OTPs for this parent
        cls.objects.filter(parent=parent).delete()
        
        # Generate a 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Create and return the OTP object
        return cls.objects.create(parent=parent, otp=otp)

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
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name='students',
        null=True,
        blank=True
    )
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
        # Generate unique admission number if not provided
        if not self.admission_number:
            base_number = f"ADM-{self.last_name[:4].upper()}-{timezone.now().year}"
            counter = 1
            admission_number = base_number
            while Student.objects.filter(admission_number=admission_number).exists():
                admission_number = f"{base_number}-{counter:03d}"
                counter += 1
            self.admission_number = admission_number
        
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
    



class YouTubeVideo(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_id = models.CharField(max_length=20, unique=True)
    published_at = models.DateTimeField()
    thumbnail_url = models.URLField(max_length=500)
    duration = models.CharField(max_length=20, blank=True)
    is_featured = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
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
    


class AcademicCalendar(models.Model):
    title = models.CharField(max_length=200)
    file = CloudinaryField(
        'academic_calendars',
        folder="academic/calendars",
        resource_type="raw",  # Important for PDFs
        blank=True,
        null=True
    )
    academic_year = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.academic_year})"

class CourseCatalog(models.Model):
    title = models.CharField(max_length=200)
    file = CloudinaryField(
        'course_catalogs',
        folder="academic/catalogs",
        resource_type="raw",  # Important for PDFs
        blank=True,
        null=True
    )
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
    TERM_CHOICES = [('1','First Term'),('2','Second Term')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    term = models.CharField(max_length=1, choices=TERM_CHOICES)
    academic_year = models.CharField(max_length=20)
    week_number = models.PositiveSmallIntegerField()
    exam_score = models.DecimalField(max_digits=5, decimal_places=2)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, editable=False)
    grade = models.CharField(max_length=2, editable=False)
    remark = models.CharField(max_length=100, editable=False)
    teacher = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='results_given')
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_results')
    date_approved = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student','subject','term','academic_year','week_number')

    def save(self, *args, **kwargs):
        self.total_score = self.exam_score  # only exam counts
        # grade logic
        if self.total_score >= Decimal('81'):
            self.grade, self.remark = 'A','Excellent'
        elif self.total_score >= Decimal('70'):
            self.grade, self.remark = 'B','Very Good'
        elif self.total_score >= Decimal('69'):
            self.grade, self.remark = 'C','Good'
        elif self.total_score >= Decimal('59'):
            self.grade, self.remark = 'D','Pass'
        else:
            self.grade, self.remark = 'F','Fail'
        super().save(*args, **kwargs)


class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Subscription for {self.user.username}"



class FeeStructure(models.Model):
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=20)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.level.name} - {self.academic_year} (TZS {self.amount})"

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('MPESA', 'M-Pesa'),
        ('BANK', 'Bank Transfer'),
        ('CASH', 'Cash'),
        ('OTHER', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE)
    control_number = models.CharField(max_length=50, unique=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateField()
    transaction_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    receipt_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.control_number} - {self.student} (TZS {self.amount_paid})"

    def save(self, *args, **kwargs):
        if not self.control_number:
            # Generate control number if not provided
            prefix = "AHMES"
            year = timezone.now().strftime('%y')
            random_part = secrets.token_hex(3).upper()
            self.control_number = f"{prefix}{year}{random_part}"
        super().save(*args, **kwargs)



from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('PASSWORD_CHANGE', 'Password Change'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.CharField(max_length=50, null=True, blank=True)  # Changed to CharField
    content_object = GenericForeignKey('content_type', 'object_id')
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} at {self.timestamp}"