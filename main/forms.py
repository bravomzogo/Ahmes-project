from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Student, StaffMember, News, Comment, Gallery, Message
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import secrets
import logging
from .models import EmailVerification
from cloudinary.forms import CloudinaryFileField  # Import CloudinaryFileField

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
    class Meta:
        model = Student
        fields = '__all__'
        exclude = ['user']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'admission_date': forms.DateInput(attrs={'type': 'date'}),
        }

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
            
            # Render-specific email sending
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
            # Only raise in production to prevent user creation if email fails
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
                'class': 'form-control'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.mp3,.mp4'
            })
        }