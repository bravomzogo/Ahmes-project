from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Campus, Level, Student, StaffMember, News, Comment
from .forms import (UserRegistrationForm, AdminRegistrationForm, StaffRegistrationForm, 
                   StudentForm, StaffMemberForm, NewsForm, CommentForm)

def is_admin(user):
    return user.is_authenticated and user.is_admin

def is_staff_member(user):
    return user.is_authenticated and user.is_staff_member

def home(request):
    news = News.objects.filter(is_published=True).order_by('-published_date')[:3]
    return render(request, 'main/index.html', {'news': news})

def about(request):
    return render(request, 'main/about.html')

def services(request):
    campuses = Campus.objects.all()
    return render(request, 'main/services.html', {'campuses': campuses})

def staff(request):
    staff_members = StaffMember.objects.all()
    return render(request, 'main/staff.html', {'staff_members': staff_members})

def contact(request):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            if request.user.is_authenticated:
                comment.author_name = request.user.username
                comment.author_email = request.user.email
            comment.save()
            messages.success(request, 'Thank you for your comment!')
            return redirect('contact')
    else:
        form = CommentForm()
    return render(request, 'main/contact.html', {'form': form})

def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_admin:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not an admin account')
    return render(request, 'main/admin_login.html')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    students_count = Student.objects.count()
    staff_count = StaffMember.objects.count()
    news_count = News.objects.count()
    pending_comments = Comment.objects.filter(is_approved=False).count()
    return render(request, 'main/admin_dashboard.html', {
        'students_count': students_count,
        'staff_count': staff_count,
        'news_count': news_count,
        'pending_comments': pending_comments,
    })

@login_required
@user_passes_test(is_admin)
def manage_students(request):
    students = Student.objects.all().order_by('-created_at')
    return render(request, 'main/manage_students.html', {'students': students})

@login_required
@user_passes_test(is_admin)
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully!')
            return redirect('manage_students')
    else:
        form = StudentForm()
    return render(request, 'main/add_student.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('manage_students')
    else:
        form = StudentForm(instance=student)
    return render(request, 'main/edit_student.html', {'form': form, 'student': student})

@login_required
@user_passes_test(is_admin)
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully!')
        return redirect('manage_students')
    return render(request, 'main/delete_student.html', {'student': student})

@login_required
@user_passes_test(is_admin)
def manage_staff(request):
    staff_members = StaffMember.objects.all().order_by('-created_at')
    return render(request, 'main/manage_staff.html', {'staff_members': staff_members})

@login_required
@user_passes_test(is_admin)
def add_staff(request):
    if request.method == 'POST':
        user_form = StaffRegistrationForm(request.POST)
        staff_form = StaffMemberForm(request.POST, request.FILES)
        if user_form.is_valid() and staff_form.is_valid():
            user = user_form.save()
            staff_member = staff_form.save(commit=False)
            staff_member.user = user
            staff_member.save()
            messages.success(request, 'Staff member added successfully!')
            return redirect('manage_staff')
    else:
        user_form = StaffRegistrationForm()
        staff_form = StaffMemberForm()
    return render(request, 'main/add_staff.html', {
        'user_form': user_form,
        'staff_form': staff_form,
    })

@login_required
@user_passes_test(is_admin)
def edit_staff(request, pk):
    staff_member = get_object_or_404(StaffMember, pk=pk)
    if request.method == 'POST':
        form = StaffMemberForm(request.POST, request.FILES, instance=staff_member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully!')
            return redirect('manage_staff')
    else:
        form = StaffMemberForm(instance=staff_member)
    return render(request, 'main/edit_staff.html', {'form': form, 'staff_member': staff_member})

@login_required
@user_passes_test(is_admin)
def delete_staff(request, pk):
    staff_member = get_object_or_404(StaffMember, pk=pk)
    if request.method == 'POST':
        staff_member.user.delete()
        messages.success(request, 'Staff member deleted successfully!')
        return redirect('manage_staff')
    return render(request, 'main/delete_staff.html', {'staff_member': staff_member})

@login_required
@user_passes_test(is_admin)
def manage_news(request):
    news_items = News.objects.all().order_by('-published_date')
    return render(request, 'main/manage_news.html', {'news_items': news_items})

@login_required
@user_passes_test(is_admin)
def add_news(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.author = request.user
            news.save()
            messages.success(request, 'News added successfully!')
            return redirect('manage_news')
    else:
        form = NewsForm()
    return render(request, 'main/add_news.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_news(request, pk):
    news = get_object_or_404(News, pk=pk)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            messages.success(request, 'News updated successfully!')
            return redirect('manage_news')
    else:
        form = NewsForm(instance=news)
    return render(request, 'main/edit_news.html', {'form': form, 'news': news})

@login_required
@user_passes_test(is_admin)
def delete_news(request, pk):
    news = get_object_or_404(News, pk=pk)
    if request.method == 'POST':
        news.delete()
        messages.success(request, 'News deleted successfully!')
        return redirect('manage_news')
    return render(request, 'main/delete_news.html', {'news': news})

@login_required
@user_passes_test(is_admin)
def manage_comments(request):
    comments = Comment.objects.all().order_by('-created_at')
    return render(request, 'main/manage_comments.html', {'comments': comments})

@login_required
@user_passes_test(is_admin)
def approve_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.is_approved = True
    comment.save()
    messages.success(request, 'Comment approved successfully!')
    return redirect('manage_comments')

@login_required
@user_passes_test(is_admin)
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
        return redirect('manage_comments')
    return render(request, 'main/delete_comment.html', {'comment': comment})

@login_required
def custom_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('logout')