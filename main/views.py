from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Campus, Gallery, Level, Student, StaffMember, News, Comment, User
from .forms import (GalleryForm, UserRegistrationForm, AdminRegistrationForm, StaffRegistrationForm, 
                   StudentForm, StaffMemberForm, NewsForm, CommentForm)
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Max, Count, Q
from .models import Conversation, Message, EmailVerification
from .forms import RegisterForm, MessageForm
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_POST
import secrets
import json
from django.utils import timezone

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        
        if not user.is_active:
            messages.error(self.request, "Account not active. Please verify your email first.")
            return redirect('login')
        
        login(self.request, user)
        messages.success(self.request, "Login successful!")
        return redirect('inbox')
    
    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)

from django.db import transaction

def register(request):
    if request.user.is_authenticated:
        return redirect('inbox')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    messages.success(request, 'Registration successful! Please check your email for verification.')
                    return redirect('verify_email')
            except Exception as e:
                messages.error(request, "An error occurred during registration. Please try again.")
                # Log the error if needed
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()
    
    return render(request, 'auth/register.html', {'form': form})

def verify_email(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            verification = EmailVerification.objects.get(code=code)
            verification.user.is_active = True
            verification.user.save()
            
            # Automatically create a conversation with admin
            admin = User.objects.filter(is_staff=True).first()
            if admin:
                conversation = Conversation.objects.create()
                conversation.participants.add(verification.user, admin)
            
            messages.success(request, "Email verified! You can now login.")
            return redirect('login')
        except EmailVerification.DoesNotExist:
            messages.error(request, "Invalid code. Please try again.")
    
    return render(request, 'auth/verify_email.html')

@login_required
def inbox(request):
    # Get all conversations for the current user
    conversations = Conversation.objects.filter(
        participants=request.user
    ).prefetch_related(
        'participants', 
        'messages',
        'messages__sender'
    ).annotate(
        last_message_time=Max('messages__timestamp')
    ).order_by('-last_message_time')

    conversations_with_other = []
    for conversation in conversations:
        # Get the other participant (not the current user)
        other_user = conversation.participants.exclude(id=request.user.id).first()
        
        # Get the last message
        last_message = conversation.messages.order_by('-timestamp').first()
        
        # Count unread messages (not sent by current user)
        unread_count = conversation.messages.filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        conversations_with_other.append({
            'conversation': conversation,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    return render(request, 'chat/inbox.html', {
        'conversations_with_other': conversations_with_other
    })

@login_required
def chat(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related('participants', 'messages__sender'), 
        id=conversation_id,
        participants=request.user
    )
    
    # Mark all unread messages as read when opening the chat
    unread_messages = conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    )
    
    if unread_messages.exists():
        unread_messages.update(is_read=True, read_at=timezone.now())
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message_id': message.id,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),  # Use ISO format
                    'sender_id': message.sender.id,
                    'is_read': message.is_read,
                    'is_me': True
                })
            return redirect('chat', conversation_id=conversation.id)
    
    return render(request, 'chat/chat.html', {
        'conversation': conversation,
        'form': MessageForm(),
        'other_user': conversation.participants.exclude(id=request.user.id).first(),
    })

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You've been logged out successfully.")
    return redirect('home')

def is_admin(user):
    return user.is_authenticated and user.is_admin

def is_staff_member(user):
    return user.is_authenticated and user.is_staff_member

# Make sure you have this form created

def home(request):
    # Get latest 3 published news items
    news = News.objects.filter(is_published=True).order_by('-published_date')[:3]
    
    # Handle contact form submission
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            if request.user.is_authenticated:
                comment.author_name = request.user.username
                comment.author_email = request.user.email
            comment.save()
            messages.success(request, 'Thank you for your comment!')
            # Redirect to prevent form resubmission
            return redirect('home')
    else:
        form = CommentForm()
    
    context = {
        'news': news,
        'form': form,
    }
    return render(request, 'main/index.html', context)

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
    gallery_count = Gallery.objects.count()
    return render(request, 'main/admin_dashboard.html', {
        'students_count': students_count,
        'staff_count': staff_count,
        'news_count': news_count,
        'pending_comments': pending_comments,
        'gallery_count': gallery_count,
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


def news_detail(request, pk):
    news = get_object_or_404(News, pk=pk, is_published=True)
    return render(request, 'main/news_detail.html', {'news': news})



@login_required
@user_passes_test(is_admin)
def manage_gallery(request):
    gallery_items = Gallery.objects.all().order_by('-published_date')
    return render(request, 'main/manage_gallery.html', {'gallery_items': gallery_items})

@login_required
@user_passes_test(is_admin)
def add_gallery(request):
    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES)
        if form.is_valid():
            gallery = form.save(commit=False)
            gallery.author = request.user
            gallery.save()
            messages.success(request, 'Gallery item added successfully!')
            return redirect('manage_gallery')
    else:
        form = GalleryForm()
    return render(request, 'main/add_gallery.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_gallery(request, pk):
    gallery = get_object_or_404(Gallery, pk=pk)
    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES, instance=gallery)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gallery item updated successfully!')
            return redirect('manage_gallery')
    else:
        form = GalleryForm(instance=gallery)
    return render(request, 'main/edit_gallery.html', {'form': form, 'gallery': gallery})

@login_required
@user_passes_test(is_admin)
def delete_gallery(request, pk):
    gallery = get_object_or_404(Gallery, pk=pk)
    if request.method == 'POST':
        gallery.delete()
        messages.success(request, 'Gallery item deleted successfully!')
        return redirect('manage_gallery')
    return render(request, 'main/delete_gallery.html', {'gallery': gallery})



def gallery(request):
    gallery_items = Gallery.objects.filter(is_published=True).order_by('-published_date')
    return render(request, 'main/gallery.html', {'gallery_items': gallery_items})



@login_required
def get_conversations(request):
    conversations = Conversation.objects.filter(
        participants=request.user
    ).prefetch_related(
        'participants', 'messages'
    ).annotate(
        last_message_time=Max('messages__timestamp'),
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-last_message_time')

    conversations_data = []
    for conversation in conversations:
        other_user = conversation.participants.exclude(id=request.user.id).first()
        last_message = conversation.messages.order_by('-timestamp').first()
        
        if last_message:
            conversations_data.append({
                'id': conversation.id,
                'other_user': {
                    'username': other_user.username if other_user else '',
                    'id': other_user.id if other_user else None,
                },
                'last_message': {
                    'id': last_message.id,
                    'content': last_message.content,
                    'timestamp': last_message.timestamp.isoformat(),
                    'sender_id': last_message.sender.id,
                    'is_read': last_message.is_read,
                    'is_me': last_message.sender == request.user,
                },
                'unread_count': conversation.unread_count,
            })

    return JsonResponse({
        'conversations': conversations_data,
    })


@login_required
def get_new_messages(request, conversation_id):
    last_id = request.GET.get('last_id', 0)
    try:
        messages = Message.objects.filter(
            conversation_id=conversation_id,
            conversation__participants=request.user,
            id__gt=last_id
        ).order_by('timestamp')
        
        messages_data = [{
            'id': m.id,
            'content': m.content,
            'timestamp': m.timestamp.isoformat(),
            'sender_id': m.sender.id,
            'is_read': m.is_read,
            'is_me': m.sender == request.user
        } for m in messages]
        
        return JsonResponse({'messages': messages_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required
def mark_messages_read(request):
    try:
        data = json.loads(request.body)
        message_ids = data.get('message_ids', [])
        
        # Update messages that belong to the user's conversations and are not sent by them
        updated = Message.objects.filter(
            id__in=message_ids,
            conversation__participants=request.user,
            is_read=False
        ).exclude(
            sender=request.user
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'updated_count': updated
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    


