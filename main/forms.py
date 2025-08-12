from pyexpat.errors import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import secrets
import logging

from main.validators import validate_pdf_extension
from .models import AcademicAnnouncement, AcademicCalendar, CourseCatalog, Level, Result, SchoolClass, Subject, User, Parent, Student, StaffMember, News, Comment, Gallery, Message, EmailVerification
from cloudinary.forms import CloudinaryFileField
from django.db import transaction
from django.core.validators import FileExtensionValidator

logger = logging.getLogger(__name__)

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class AdminRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_admin = True
        if commit:
            user.save()
        return user

class StaffRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff_member = True
        if commit:
            user.save()
        return user

class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_editing = bool(self.instance.pk)
        
        if not self.is_editing:
            # Add parent fields only for new students
            self.fields['parent_name'] = forms.CharField(max_length=200, required=True)
            self.fields['parent_phone'] = forms.CharField(max_length=20, required=True)
            self.fields['parent_email'] = forms.EmailField(required=True)
            self.fields['parent_address'] = forms.CharField(widget=forms.Textarea, required=True)
            self.fields['parent_profile_picture'] = CloudinaryFileField(
                options={
                    'folder': 'school/parents/profile_pictures',
                    'transformation': {'quality': 'auto:good', 'width': 300, 'height': 300, 'crop': 'fill'},
                    'overwrite': True,
                    'resource_type': 'image',
                },
                required=False,
                widget=forms.ClearableFileInput
            )

    profile_picture = CloudinaryFileField(
        options={
            'folder': 'school/students/profile_pictures',
            'transformation': {'quality': 'auto:good', 'width': 300, 'height': 300, 'crop': 'fill'},
            'overwrite': True,
            'resource_type': 'image',
        },
        required=False,
        widget=forms.ClearableFileInput
    )

    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth',
            'admission_number', 'campus', 'level', 'admission_date', 'profile_picture'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'admission_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_parent_email(self):
        if not self.is_editing and 'parent_email' in self.cleaned_data:
            email = self.cleaned_data.get('parent_email').lower()
            if Parent.objects.filter(email=email).exclude(id=self.instance.parent_id if self.instance else None).exists():
                raise forms.ValidationError("A parent with this email already exists.")
            if User.objects.filter(email=email).exclude(id=self.instance.user_id if self.instance else None).exists():
                raise forms.ValidationError("A user with this email already exists.")
            return email

    def clean_admission_number(self):
        admission_number = self.cleaned_data.get('admission_number')
        if admission_number and Student.objects.filter(admission_number=admission_number).exclude(id=self.instance.id if self.instance else None).exists():
            raise forms.ValidationError("A student with this admission number already exists.")
        return admission_number

    def save(self, commit=True):
        if self.is_editing:
            # For editing existing student - simple save
            student = super().save(commit=commit)
            return student
        else:
            # For creating new student - original logic with parent creation
            with transaction.atomic():
                logger.debug(f"Starting save for StudentForm with data: {self.cleaned_data}")
                
                # Create or update Parent instance
                parent_data = {
                    'name': self.cleaned_data['parent_name'],
                    'phone': self.cleaned_data['parent_phone'],
                    'email': self.cleaned_data['parent_email'],
                    'address': self.cleaned_data['parent_address'],
                    'profile_picture': self.cleaned_data['parent_profile_picture'],
                }
                logger.debug(f"Parent data: {parent_data}")
                
                parent, created = Parent.objects.get_or_create(
                    email=parent_data['email'],
                    defaults=parent_data
                )
                
                if not created:
                    for key, value in parent_data.items():
                        if key != 'profile_picture' or value:
                            setattr(parent, key, value)
                    parent.save()
                logger.debug(f"Parent {'created' if created else 'updated'}: {parent}")

                # Create or update Parent User
                parent_user = parent.user
                parent_username = None
                parent_password = None
                
                if not parent_user:
                    parent_username = parent.name.replace(' ', '').lower()
                    counter = 1
                    while User.objects.filter(username=parent_username).exists():
                        parent_username = f"{parent.name.replace(' ', '').lower()}{counter}"
                        counter += 1
                    
                    parent_password = secrets.token_urlsafe(3)
                    parent_user = User.objects.create_user(
                        username=parent_username,
                        email=parent.email,
                        password=parent_username+parent_password,
                        first_name=parent.name.split()[0],
                        last_name=parent.name.split()[-1] if len(parent.name.split()) > 1 else '',
                        is_parent=True 
                    )
                    parent.user = parent_user
                    parent.save()
                    logger.debug(f"Parent user created: {parent_username}")

                # Create Student instance
                student = super().save(commit=False)
                student.parent = parent
                logger.debug(f"Student instance prepared: {student}")

                # Create or update Student User
                student_user = student.user
                student_username = None
                student_password = None
                
                if not student_user:
                    student_username = student.last_name.lower()
                    counter = 1
                    while User.objects.filter(username=student_username).exists():
                        student_username = f"{student.last_name.lower()}{counter}"
                        counter += 1
                    
                    student_password = secrets.token_urlsafe(3)
                    student_user = User.objects.create_user(
                        username=student_username,
                        email=parent.email,
                        password=student_username+student_password,
                        first_name=student.first_name,
                        last_name=student.last_name
                    )
                    student.user = student_user
                    logger.debug(f"Student user created: {student_username}")

                if commit:
                    try:
                        student.save()
                        logger.debug(f"Student saved: {student}")
                    except Exception as e:
                        logger.error(f"Failed to save student: {str(e)}")
                        raise

                    # Send credentials email
                    try:
                        send_mail(
                            subject='School Account Credentials for You and Your Child',
                            message=render_to_string('emails/credentials.txt', {
                                'student': student,
                                'student_username': student_username,
                                'student_password': student_password,
                                'parent': parent,
                                'parent_username': parent_username,
                                'parent_password': parent_password,
                                'support_email': settings.DEFAULT_FROM_EMAIL
                            }),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[parent.email],
                            html_message=render_to_string('emails/credentials.html', {
                                'student': student,
                                'student_username': student_username,
                                'student_password': student_password,
                                'parent': parent,
                                'parent_username': parent_username,
                                'parent_password': parent_password,
                                'support_email': settings.DEFAULT_FROM_EMAIL
                            }),
                            fail_silently=False,
                        )
                        logger.info(f"Credentials email sent to {parent.email}")
                    except Exception as e:
                        logger.error(f"Failed to send credentials email to {parent.email}: {str(e)}")

                return student

class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'joined_date': forms.DateInput(attrs={'type': 'date'}),
        }

class NewsForm(forms.ModelForm):
    image = CloudinaryFileField(
        options={
            'folder': 'school/news',
            'resource_type': 'image',
            'overwrite': True,
        },
        required=False
    )
    
    class Meta:
        model = News
        fields = ['title', 'content', 'image', 'is_published']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'author_name', 'author_email']

class GalleryForm(forms.ModelForm):
    image = CloudinaryFileField(
        options={
            'folder': 'school/gallery/images',
            'resource_type': 'image',
            'overwrite': True,
        },
        required=False
    )
    
    video = CloudinaryFileField(
        options={
            'folder': 'school/gallery/videos',
            'resource_type': 'video',
            'overwrite': True,
        },
        required=False
    )
    
    class Meta:
        model = Gallery
        fields = ['title', 'description', 'media_type', 'image', 'video', 'is_published']
        widgets = {
            'media_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')

        if media_type == 'image' and not image:
            raise forms.ValidationError("An image is required for image media type.")
        if media_type == 'video' and not video:
            raise forms.ValidationError("A video is required for video media type.")
        if media_type == 'image' and video:
            raise forms.ValidationError("Video should not be provided for image media type.")
        if media_type == 'video' and image:
            raise forms.ValidationError("Image should not be provided for video media type.")
        return cleaned_data

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.is_active = False

        if commit:
            user.save()
            verification_code = str(secrets.randbelow(900000) + 100000)
            EmailVerification.objects.create(
                user=user,
                code=verification_code,
                activation_code_expires=timezone.now() + timedelta(hours=24)
            )
            self.send_verification_email(user)
        return user

    def send_verification_email(self, user):
        try:
            verification = EmailVerification.objects.get(user=user)
            context = {
                'user': user,
                'verification_code': verification.code,
                'expiration_hours': 24,
                'support_email': settings.DEFAULT_FROM_EMAIL
            }
            
            send_mail(
                subject='Verify Your Ahmes School Account',
                message=render_to_string('emails/verification_email.txt', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=render_to_string('emails/verification_email.html', context),
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent to {user.email}")
        
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            if not settings.DEBUG:
                raise forms.ValidationError(
                    "We couldn't send the verification email. Please try again later."
                )

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'file']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Type your message...',
                'class': 'form-control',
                'id': 'messageInput'
            }),
            'file': forms.FileInput(attrs={
                'class': 'd-none',
                'id': 'fileInput',
                'accept': '.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.mp3,.mp4,.mov,.avi'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = False
        self.fields['file'].validators = [
            FileExtensionValidator(allowed_extensions=[
                'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx',
                'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'mp3', 'mp4', 'mov', 'avi'
            ])
        ]
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            max_size = 25 * 1024 * 1024  # 25MB
            if file.size > max_size:
                raise forms.ValidationError(f"File too large. Maximum size is {max_size/1024/1024}MB.")
        return file

class SchoolClassForm(forms.ModelForm):
    level = forms.ModelChoiceField(
        queryset=Level.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'id': 'id_level_filter',
            'hx-get': '/students/filter_by_level/',
            'hx-target': '#id_students',
            'hx-trigger': 'change'
        })
    )
    
    class Meta:
        model = SchoolClass
        fields = ['name', 'level', 'teacher', 'students', 'academic_year']
        widgets = {
            'teacher': forms.Select(),
            'students': forms.SelectMultiple(attrs={
                'id': 'id_students',
                'size': 10,
                'style': 'width: 100%'
            }),
            'academic_year': forms.TextInput(attrs={'placeholder': 'e.g., 2025-2026'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we have a level in the initial data or POST data, filter students
        if 'level' in self.data:
            try:
                level_id = int(self.data.get('level'))
                self.fields['students'].queryset = Student.objects.filter(level_id=level_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.level:
            self.fields['students'].queryset = Student.objects.filter(level=self.instance.level)
        else:
            self.fields['students'].queryset = Student.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get('level')
        students = cleaned_data.get('students')
        
        if level and students:
            # Verify all selected students belong to the selected level
            invalid_students = students.exclude(level=level)
            if invalid_students.exists():
                raise forms.ValidationError(
                    f"The following students don't belong to level {level}: "
                    f"{', '.join(str(s) for s in invalid_students)}"
                )
        return cleaned_data

class AcademicAnnouncementForm(forms.ModelForm):
    class Meta:
        model = AcademicAnnouncement
        fields = ['title', 'content', 'date', 'is_published']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'is_published': forms.CheckboxInput(),
        }

class AcademicCalendarForm(forms.ModelForm):
    file = CloudinaryFileField(
        options={
            'folder': 'academic/calendars',
            'resource_type': 'raw',
            'overwrite': True,
        },
        required=True,
        validators=[validate_pdf_extension]  # Use our custom validator
    )
    
    class Meta:
        model = AcademicCalendar
        fields = ['title', 'file', 'academic_year', 'is_active']

class CourseCatalogForm(forms.ModelForm):
    file = CloudinaryFileField(
        options={
            'folder': 'academic/catalogs',
            'resource_type': 'raw',
            'overwrite': True,
        },
        required=True,
        validators=[validate_pdf_extension]  # Use our custom validator
    )
    
    class Meta:
        model = CourseCatalog
        fields = ['title', 'file', 'academic_year', 'is_active']

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description', 'level']



class ResultApprovalForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['is_approved']


# forms.py
from django import forms
import pandas as pd
from io import BytesIO

class StudentImportForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel File',
        help_text='Upload an Excel file with student data. The file should have columns matching the student fields.'
    )

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError("Only Excel files are allowed (.xlsx, .xls)")
        
        try:
            # Read Excel file with explicit date format parsing
            df = pd.read_excel(
                BytesIO(excel_file.read()),
                parse_dates=['date_of_birth', 'admission_date'],
                date_format='%d/%m/%Y'  # Specify DD/MM/YYYY format
            )
            required_columns = [
                'first_name', 'last_name', 'gender', 'date_of_birth',
                'campus', 'level', 'admission_date',
                'parent_name', 'parent_phone', 'parent_email'
            ]
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise forms.ValidationError(f"Missing required columns: {', '.join(missing_columns)}")
            
            return df
        except Exception as e:
            raise forms.ValidationError(f"Error reading Excel file: {str(e)}")


class WeeklyResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['school_class', 'student', 'subject', 'term', 'academic_year', 'week_number', 'exam_score']
        widgets = {
            'academic_year': forms.TextInput(attrs={'placeholder': 'e.g., 2024-2025'}),
            'week_number': forms.NumberInput(attrs={'min': 1, 'max': 15}),
            'exam_score': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 0.01}),
        }
    
    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if teacher:
            # Filter classes to only those taught by this teacher
            self.fields['school_class'].queryset = SchoolClass.objects.filter(teacher=teacher)
            
            # Set required fields
            self.fields['school_class'].required = True
            self.fields['student'].required = True
            self.fields['subject'].required = True
            self.fields['term'].required = True
            self.fields['academic_year'].required = True
            self.fields['week_number'].required = True
            self.fields['exam_score'].required = True
            
            # Add class to enable select2
            for field in self.fields.values():
                field.widget.attrs['class'] = 'form-select'


