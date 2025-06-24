from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Student, StaffMember, News, Comment

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