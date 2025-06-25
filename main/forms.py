from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Student, StaffMember, News, Comment , Gallery

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
    class Meta:
        model = News
        fields = ['title', 'content', 'image', 'is_published']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'author_name', 'author_email']



class GalleryForm(forms.ModelForm):
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