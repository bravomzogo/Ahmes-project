from venv import logger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views import View

from main.utils import send_otp_via_email

from .models import AcademicAnnouncement, AcademicCalendar, Campus, CourseCatalog, FeeStructure, Gallery, InventoryCategory, InventoryItem, InventoryTransaction, Level, Parent, ParentOTP, Payment, PushSubscription, Result, SchoolClass, Student, StaffMember, News, Comment, Subject, User
from .forms import (GalleryForm, ResultApprovalForm, StaffRegistrationForm, 
                   StudentForm, StaffMemberForm, NewsForm, CommentForm, WeeklyResultForm)
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.db.models import Max, Count, Q
from .models import Conversation, Message, EmailVerification
from .forms import RegisterForm, MessageForm
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_POST
import secrets
import json
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.forms import AuthenticationForm
from weasyprint import HTML
from django.template.loader import render_to_string
from django.urls import reverse

from main import models

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

    # Calculate total unread messages across all conversations
    total_unread = Message.objects.filter(
        conversation__participants=request.user,
        is_read=False
    ).exclude(
        sender=request.user
    ).count()

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
        'conversations_with_other': conversations_with_other,
        # 'unread_messages_count': total_unread  # Add this to context
    })
@login_required
def chat(request, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related('participants', 'messages__sender'),
        id=conversation_id,
        participants=request.user
    )

    unread_messages = conversation.messages.filter(is_read=False).exclude(sender=request.user)
    if unread_messages.exists():
        unread_messages.update(is_read=True, read_at=timezone.now())

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
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
                    'timestamp': message.timestamp.isoformat(),
                    'sender_id': message.sender.id,
                    'is_read': message.is_read,
                    'file_url': message.file_url,
                    'file_name': message.file_name,
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
    # Get latest 5 published news items for the ticker
    latest_news = News.objects.filter(is_published=True).order_by('-published_date')[:5]
    
    # Get latest 3 published news items for the news section
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
            return redirect('home')
    else:
        form = CommentForm()
    
    context = {
        'latest_news': latest_news,
        'news': news,
        'form': form,
    }
    return render(request, 'main/index.html', context)

def about(request):
    return render(request, 'main/about.html')

def services(request):
    campuses = Campus.objects.all()
    return render(request, 'main/services.html', {'campuses': campuses})

from django.shortcuts import render
from .models import StaffMember

def staff(request):
    # Fetch and categorize staff
    staff_members = StaffMember.objects.select_related('user', 'campus')
    teachers = staff_members.filter(position='Teacher')
    admins = staff_members.filter(position='Administrator')
    supports = staff_members.filter(position='Support')

    return render(request, 'main/staff.html', {
        'teachers': teachers,
        'admins': admins,
        'supports': supports,
        'teacher_count': teachers.count(),
        'admin_count': admins.count(),
        'support_count': supports.count(),
    })

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
    # Fetch recent activities (last 10)
    from .models import ActivityLog
    recent_activities = ActivityLog.objects.all().order_by('-timestamp')[:10]
    activities_count = ActivityLog.objects.count()
    return render(request, 'main/admin_dashboard.html', {
        'students_count': students_count,
        'staff_count': staff_count,
        'news_count': news_count,
        'pending_comments': pending_comments,
        'activities_count': activities_count,
        'recent_activities': recent_activities,
        'gallery_count': gallery_count,
    })

@login_required
@user_passes_test(is_admin)
def manage_students(request):
    query = request.GET.get('q')
    students = Student.objects.all()

    if query:
        students = students.filter(
            first_name__icontains=query
        ) | students.filter(
            middle_name__icontains=query
        ) | students.filter(
            last_name__icontains=query
        ) | students.filter(
            admission_number__icontains=query
        )

    students = students.order_by('-created_at')
    return render(request, 'main/manage_students.html', {'students': students, 'query': query})

# views.py
from .forms import StudentImportForm
from django.db import transaction

@login_required
@user_passes_test(is_admin)
def add_student(request):
    excel_form = StudentImportForm()
    single_form = StudentForm()
    
    if request.method == 'POST':
        if 'excel_submit' in request.POST:
            excel_form = StudentImportForm(request.POST, request.FILES)
            if excel_form.is_valid():
                try:
                    df = excel_form.cleaned_data['excel_file']
                    logger.debug(f"Excel file has {len(df)} rows")
                    created_count = 0
                    
                    for index, row in df.iterrows():
                        # Handle campus
                        campus_name = str(row['campus']).strip()
                        try:
                            campus = Campus.objects.get(name=campus_name)
                        except Campus.DoesNotExist:
                            messages.error(request, f"Row {index + 2}: Campus '{campus_name}' not found.")
                            logger.error(f"Campus '{campus_name}' not found for row {index + 2}")
                            continue
                        
                        # Handle level
                        level_name = str(row['level']).strip()
                        try:
                            level = Level.objects.get(name=level_name)
                        except Level.DoesNotExist:
                            messages.error(request, f"Row {index + 2}: Level '{level_name}' not found.")
                            logger.error(f"Level '{level_name}' not found for row {index + 2}")
                            continue
                        
                        # Prepare student data with IDs
                        student_data = {
                            'first_name': str(row['first_name']).strip(),
                            'last_name': str(row['last_name']).strip(),
                            'gender': str(row['gender']).strip().upper(),
                            'date_of_birth': row['date_of_birth'],
                            'campus': campus.id,
                            'level': level.id,
                            'admission_date': row['admission_date'],
                            'parent_name': str(row['parent_name']).strip(),
                            'parent_phone': str(row['parent_phone']).strip(),
                            'parent_email': str(row['parent_email']).strip().lower(),
                            'middle_name': str(row.get('middle_name', '')).strip(),
                            'admission_number': str(row.get('admission_number', '')).strip(),
                            'parent_address': str(row.get('parent_address', '')).strip(),
                        }
                        logger.debug(f"Row {index + 2}: Processing student data: {student_data}")
                        
                        form = StudentForm(student_data)
                        if form.is_valid():
                            try:
                                with transaction.atomic():
                                    form.save()
                                created_count += 1
                                logger.debug(f"Row {index + 2}: Student saved successfully")
                            except Exception as e:
                                messages.error(request, f"Row {index + 2}: Error saving student: {str(e)}")
                                logger.error(f"Row {index + 2}: Error saving student: {str(e)}")
                        else:
                            messages.error(request, f"Row {index + 2}: Invalid data: {form.errors.as_text()}")
                            logger.error(f"Row {index + 2}: Form invalid. Errors: {form.errors.as_text()}")
                    
                    if created_count > 0:
                        messages.success(request, f"Successfully imported {created_count} students!")
                    else:
                        messages.warning(request, "No students were imported. Check the error messages above.")
                    return redirect('manage_students')
                    
                except Exception as e:
                    messages.error(request, f"Error during import: {str(e)}")
                    logger.error(f"Error during import: {str(e)}")
        
        elif 'single_submit' in request.POST:
            single_form = StudentForm(request.POST, request.FILES)
            if single_form.is_valid():
                try:
                    with transaction.atomic():
                        student = single_form.save()
                    messages.success(request, "Student and parent added successfully! Credentials sent to parent email.")
                    return redirect('manage_students')
                except Exception as e:
                    messages.error(request, f"Error adding student: {str(e)}")
    
    return render(request, 'main/add_student.html', {
        'excel_form': excel_form,
        'single_form': single_form,
        'title': 'Add New Student'
    })

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
    
    return render(request, 'main/edit_student.html', {
        'form': form,
        'student': student,
        'title': f'Edit Student: {student.first_name} {student.last_name}'
    })
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
    


def under_development(request):
    return render(request, 'main/under_development.html')




@require_POST
@login_required
def handle_typing(request):
    conversation_id = request.POST.get('conversation_id')
    is_typing = request.POST.get('is_typing') == 'true'
    
    # Store typing status in cache with a short expiration
    cache_key = f'typing_{conversation_id}_{request.user.id}'
    cache.set(cache_key, is_typing, timeout=3)  # 3 seconds expiration
    
    return JsonResponse({'success': True})

@login_required
def get_typing_status(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    # Check if other user is typing
    cache_key = f'typing_{conversation_id}_{other_user.id}'
    is_typing = cache.get(cache_key, False)
    
    return JsonResponse({
        'is_typing': is_typing,
        'user_id': other_user.id
    })
    

from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import YouTubeVideo

def is_admin(user):
    return user.is_authenticated and user.is_admin

def ahmes_tv(request):
    page = request.GET.get('page', 1)
    search_query = request.GET.get('search', '')
    
    # Only show approved videos to regular users
    videos = YouTubeVideo.objects.filter(
        (Q(title__icontains='AHMES') | Q(description__icontains='AHMES')),
        is_approved=True
    )
    
    if search_query:
        videos = videos.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    videos = videos.order_by('-published_at')
    
    paginator = Paginator(videos, 9)
    try:
        videos_page = paginator.page(page)
    except PageNotAnInteger:
        videos_page = paginator.page(1)
    except EmptyPage:
        videos_page = paginator.page(paginator.num_pages)
    
    context = {
        'videos': videos_page,
        'search_query': search_query,
        'paginator': paginator,
        'page_obj': videos_page,
    }
    
    return render(request, 'main/ahmes_tv.html', context)

@login_required
@user_passes_test(is_admin)
def manage_youtube_videos(request):
    videos = YouTubeVideo.objects.all().order_by('-published_at')
    return render(request, 'main/manage_youtube_videos.html', {'videos': videos})

@login_required
@user_passes_test(is_admin)
def approve_youtube_video(request, video_id):
    video = get_object_or_404(YouTubeVideo, id=video_id)
    if not video.is_approved:
        video.is_approved = True
        video.approved_by = request.user
        video.approved_at = timezone.now()
        video.save()
        messages.success(request, f'Video "{video.title}" has been approved!')
    else:
        messages.warning(request, f'Video "{video.title}" was already approved.')
    return redirect('manage_youtube_videos')

@login_required
@user_passes_test(is_admin)
def reject_youtube_video(request, video_id):
    video = get_object_or_404(YouTubeVideo, id=video_id)
    if request.method == 'POST':
        video.delete()
        messages.success(request, f'Video "{video.title}" has been rejected and deleted.')
        return redirect('manage_youtube_videos')
    return render(request, 'main/confirm_reject_video.html', {'video': video})



from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required

class StudentLoginView(LoginView):
    template_name = 'academics/student_login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        if not hasattr(user, 'student_profile'):
            messages.error(self.request, "This account doesn't have student access.")
            return redirect('student_login')
        login(self.request, user)
        return redirect('student_dashboard')

class TeacherLoginView(LoginView):
    template_name = 'academics/teacher_login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        staff_profile = getattr(user, 'staff_profile', None)
        if not staff_profile or staff_profile.position != 'Teacher':
            messages.error(self.request, "This account doesn't have teacher access.")
            return redirect('teacher_login')
        login(self.request, user)
        return redirect('teacher_dashboard')



# Parent Login View (updated with forgot password link)
class ParentLoginView(View):
    template_name = 'academics/parent_login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_parent:
                logger.debug(f"Authenticated parent {request.user.username} redirected to dashboard")
                return redirect('parent_dashboard')
            else:
                messages.error(request, 'This page is for parent accounts only.')
                logger.warning(f"Non-parent user {request.user.username} attempted parent login")
                return redirect('home')
        form = AuthenticationForm()
        return render(request, self.template_name, {
            'form': form,
            'title': 'Parent Login'
        })

    def post(self, request, *args, **kwargs):
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_parent:
                    login(request, user)
                    if not request.POST.get('remember'):
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(1209600)
                    logger.info(f"Parent {username} logged in successfully")
                    next_url = request.POST.get('next', 'parent_dashboard')
                    return redirect(next_url)
                else:
                    messages.error(request, 'This account is not a parent account.')
                    logger.warning(f"Non-parent user {username} attempted parent login")
            else:
                messages.error(request, 'Invalid username or password.')
                logger.error(f"Invalid login attempt for username {username}")
        else:
            messages.error(request, 'Please correct the errors below.')
            logger.debug(f"Form validation failed: {form.errors.as_text()}")

        return render(request, self.template_name, {
            'form': form,
            'title': 'Parent Login'
        })

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db.models import Q
from .models import Parent, ParentOTP
from .utils import send_otp_via_email
import logging

logger = logging.getLogger(__name__)

class ParentPasswordResetRequestView(View):
    template_name = 'academics/parent_password_reset_request.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email').strip()
        logger.info(f"Password reset requested for email: {email}")
        
        try:
            # Find parent by email (check both user email and parent email)
            parent = Parent.objects.get(
                Q(email=email) | 
                Q(user__email=email)
            )
            
            # Get the actual email to use (prefer user email if available)
            send_to_email = parent.user.email if parent.user and parent.user.email else parent.email
            
            # Use the email from the form submission to ensure we send to the correct address
            if email != send_to_email:
                logger.warning(f"Email mismatch: form={email}, parent={send_to_email}. Using form email.")
                send_to_email = email
            
            logger.info(f"Generating OTP for parent {parent.name}, sending to: {send_to_email}")
            otp_obj = ParentOTP.generate_otp(parent, send_to_email)
            
            # Send OTP via Email
            email_sent = send_otp_via_email(send_to_email, otp_obj.otp)
            
            if email_sent:
                request.session['reset_parent_id'] = parent.id
                request.session['reset_email'] = send_to_email  # Store the email for verification
                messages.success(request, f'OTP has been sent to your email address: {send_to_email}')
                logger.info(f"OTP sent successfully to {send_to_email} for parent {parent.name}")
            else:
                # Still continue the process but show a warning
                request.session['reset_parent_id'] = parent.id
                request.session['reset_email'] = send_to_email
                messages.warning(request, 'OTP generated but there was an issue sending email. Please check the console for your OTP.')
                logger.warning(f"OTP generated but email failed for {send_to_email}: {otp_obj.otp}")
            
            return redirect('parent_verify_otp')
            
        except Parent.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
            logger.warning(f"Password reset attempt for unknown email: {email}")
            return render(request, self.template_name, {'email': email})
        except Parent.MultipleObjectsReturned:
            # Handle case where email exists in both parent and user
            parents = Parent.objects.filter(
                Q(email=email) | 
                Q(user__email=email)
            )
            parent = parents.first()  # Use the first one
            send_to_email = parent.user.email if parent.user and parent.user.email else parent.email
            
            # Use the email from the form submission
            if email != send_to_email:
                send_to_email = email
            
            otp_obj = ParentOTP.generate_otp(parent, send_to_email)
            email_sent = send_otp_via_email(send_to_email, otp_obj.otp)
            
            if email_sent:
                request.session['reset_parent_id'] = parent.id
                request.session['reset_email'] = send_to_email
                messages.success(request, f'OTP has been sent to your email address: {send_to_email}')
            else:
                request.session['reset_parent_id'] = parent.id
                request.session['reset_email'] = send_to_email
                messages.warning(request, 'OTP generated but email sending failed. Check console for OTP.')
            
            return redirect('parent_verify_otp')


class ParentVerifyOTPView(View):
    template_name = 'academics/parent_verify_otp.html'
    
    def get(self, request):
        if 'reset_parent_id' not in request.session:
            messages.error(request, 'Please request OTP first.')
            return redirect('parent_password_reset_request')
        
        # Show the email address where OTP was sent
        email = request.session.get('reset_email', 'your email')
        return render(request, self.template_name, {'email': email})
    
    def post(self, request):
        otp = request.POST.get('otp')
        parent_id = request.session.get('reset_parent_id')
        email = request.session.get('reset_email')
        
        try:
            parent = Parent.objects.get(id=parent_id)
            # Get the latest unused OTP for this parent
            otp_obj = ParentOTP.objects.filter(
                parent=parent, 
                is_used=False
            ).latest('created_at')
            
            # Check if OTP matches and is valid
            if otp_obj.otp == otp and otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                request.session['otp_verified'] = True
                messages.success(request, 'OTP verified successfully. You can now reset your password.')
                return redirect('parent_reset_password')
            else:
                messages.error(request, 'Invalid or expired OTP.')
                return render(request, self.template_name, {'email': email})
                
        except ParentOTP.DoesNotExist:
            messages.error(request, 'Invalid OTP or OTP has expired.')
            return render(request, self.template_name, {'email': email})
        except Parent.DoesNotExist:
            messages.error(request, 'Invalid session. Please request OTP again.')
            return redirect('parent_password_reset_request')


class ParentPasswordResetView(View):
    template_name = 'academics/parent_reset_password.html'
    
    def get(self, request):
        if not request.session.get('otp_verified'):
            messages.error(request, 'Please verify OTP first.')
            return redirect('parent_password_reset_request')
        return render(request, self.template_name)
    
    def post(self, request):
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, self.template_name)
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, self.template_name)
        
        parent_id = request.session.get('reset_parent_id')
        try:
            parent = Parent.objects.get(id=parent_id)
            user = parent.user
            
            if not user:
                messages.error(request, 'No user account associated with this parent.')
                return render(request, self.template_name)
            
            user.set_password(password)
            user.save()
            
            # Clear session data
            request.session.pop('reset_parent_id', None)
            request.session.pop('reset_email', None)
            request.session.pop('otp_verified', None)
            
            messages.success(request, 'Password reset successfully. You can now login with your new password.')
            return redirect('parent_login')
            
        except Parent.DoesNotExist:
            messages.error(request, 'Invalid session. Please request password reset again.')
            return redirect('parent_password_reset_request')

class AcademicAdminLoginView(LoginView):
    template_name = 'academics/academic_admin_login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        staff_profile = getattr(user, 'staff_profile', None)
        if not user.is_admin and (not staff_profile or staff_profile.position != 'Administrator'):
            messages.error(self.request, "This account doesn't have academic admin access.")
            return redirect('academic_admin_login')
        login(self.request, user)
        return redirect('academic_admin_dashboard')

@login_required
def student_dashboard(request):
    if not hasattr(request.user, 'student_profile'):
        raise PermissionDenied
    student = request.user.student_profile
    return render(request, 'academics/student_dashboard.html', {'student': student})

@login_required
def teacher_dashboard(request):
    staff_profile = getattr(request.user, 'staff_profile', None)
    if not staff_profile or staff_profile.position != 'Teacher':
        raise PermissionDenied
    
    # Get classes taught by this teacher
    classes_taught = SchoolClass.objects.filter(teacher=staff_profile)
    return render(request, 'academics/teacher_dashboard.html', {
        'staff': staff_profile,
        'classes_taught': classes_taught
    })

@login_required
def parent_dashboard(request):
    try:
        parent = request.user.parent_profile
    except Parent.DoesNotExist:
        raise PermissionDenied("No parent profile found for this account.")

    students = Student.objects.filter(parent=parent)
    if not students.exists():
        raise PermissionDenied("No students associated with this parent account.")

    # Get fee structures for the students' levels
    fee_structures = FeeStructure.objects.filter(
        level__in=students.values_list('level', flat=True),
        is_active=True
    ).distinct()

    # Get all payments for the students
    payments = Payment.objects.filter(
        student__in=students
    ).order_by('-payment_date')

    # Get announcements (your existing code)
    announcements = AcademicAnnouncement.objects.filter(is_published=True).order_by('-date')[:5]

    return render(request, 'academics/parent_dashboard.html', {
        'students': students,
        'fee_structures': fee_structures,
        'payments': payments,
        'announcements': announcements
    })


@login_required
@require_POST
def initiate_payment(request):
    try:
        parent = request.user.parent_profile
        student_id = request.POST.get('student')
        fee_structure_id = request.POST.get('fee_structure')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        reference = request.POST.get('transaction_reference', '')

        # Validate the student belongs to the parent
        student = get_object_or_404(Student, id=student_id, parent=parent)
        fee_structure = get_object_or_404(FeeStructure, id=fee_structure_id, is_active=True)

        # Create the payment record
        payment = Payment.objects.create(
            student=student,
            fee_structure=fee_structure,
            amount_paid=amount,
            payment_method=payment_method,
            payment_date=timezone.now().date(),
            transaction_reference=reference,
            status='PENDING'
        )

        # Here you would typically integrate with a payment gateway
        # For now, we'll just return the control number
        messages.success(request, f"Payment initiated successfully. Your control number is {payment.control_number}")
        
        # Send push notification
        send_push_notification(
            user=request.user,
            title="Payment Initiated",
            message=f"Payment of TZS {amount} initiated for {student.first_name}",
            url=reverse('parent_dashboard')
        )

        return redirect('parent_dashboard')

    except Exception as e:
        messages.error(request, f"Error initiating payment: {str(e)}")
        return redirect('parent_dashboard')



@login_required
def academic_admin_dashboard(request):
    if not (request.user.is_admin or 
            (hasattr(request.user, 'staff_profile') and 
             request.user.staff_profile.position == 'Administrator')):
        raise PermissionDenied
    
    # Academic admin statistics
    total_students = Student.objects.count()
    total_teachers = StaffMember.objects.filter(position='Teacher').count()
    active_classes = SchoolClass.objects.count()
    academic_announcements = AcademicAnnouncement.objects.filter(is_published=True).count()
    active_catalogs = CourseCatalog.objects.filter(is_active=True).count()
    active_calendars = AcademicCalendar.objects.filter(is_active=True).count()
    
    return render(request, 'academics/academic_admin_dashboard.html', {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'active_classes': active_classes,
        'academic_announcements': academic_announcements,
        'active_catalogs': active_catalogs,
        'active_calendars': active_calendars,
    })

def academic_services(request):
    # Get any academic-specific data you need
    academic_resources = {
        'catalogs': CourseCatalog.objects.all(),
        'calendars': AcademicCalendar.objects.all(),
        'announcements': AcademicAnnouncement.objects.filter(is_published=True)
    }
    return render(request, 'main/academic_services.html', academic_resources)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import SchoolClass, AcademicAnnouncement, CourseCatalog, AcademicCalendar
from .forms import SchoolClassForm, AcademicAnnouncementForm, CourseCatalogForm, AcademicCalendarForm

def is_academic_admin(user):
    return user.is_authenticated and (
        user.is_admin or 
        (hasattr(user, 'staff_profile') and user.staff_profile.position == 'Administrator')
    )

# Dashboard
@login_required
@user_passes_test(is_academic_admin)
def academic_admin_dashboard(request):
    active_classes = SchoolClass.objects.count()
    academic_announcements = AcademicAnnouncement.objects.filter(is_published=True).count()
    active_catalogs = CourseCatalog.objects.filter(is_active=True).count()
    active_calendars = AcademicCalendar.objects.filter(is_active=True).count()
    
    return render(request, 'academics/academic_admin_dashboard.html', {
        'active_classes': active_classes,
        'academic_announcements': academic_announcements,
        'active_catalogs': active_catalogs,
        'active_calendars': active_calendars,
    })

# --- Class Management ---
@login_required
@user_passes_test(is_academic_admin)
def manage_classes(request):
    classes = SchoolClass.objects.all().order_by('-created_at')
    return render(request, 'main/manage_classes.html', {'classes': classes})

@login_required
@user_passes_test(is_academic_admin)
def add_class(request):
    if request.method == 'POST':
        form = SchoolClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class added successfully!')
            return redirect('manage_classes')
    else:
        form = SchoolClassForm()
    
    return render(request, 'main/add_class.html', {'form': form})

@login_required
@user_passes_test(is_academic_admin)
def edit_class(request, pk):
    class_obj = get_object_or_404(SchoolClass, pk=pk)
    if request.method == 'POST':
        form = SchoolClassForm(request.POST, instance=class_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class updated successfully!')
            return redirect('manage_classes')
    else:
        form = SchoolClassForm(instance=class_obj)
    return render(request, 'main/edit_class.html', {'form': form, 'class': class_obj})

@login_required
@user_passes_test(is_academic_admin)
def delete_class(request, pk):
    class_obj = get_object_or_404(SchoolClass, pk=pk)
    if request.method == 'POST':
        class_obj.delete()
        messages.success(request, 'Class deleted successfully!')
        return redirect('manage_classes')
    return render(request, 'main/delete_class.html', {'class': class_obj})

# --- Academic Announcements ---
@login_required
@user_passes_test(is_academic_admin)
def manage_academic_announcements(request):
    announcements = AcademicAnnouncement.objects.all().order_by('-created_at')
    return render(request, 'main/manage_academic_announcements.html', {'announcements': announcements})

@login_required
@user_passes_test(is_academic_admin)
def add_academic_announcement(request):
    if request.method == 'POST':
        form = AcademicAnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.save()
            messages.success(request, 'Announcement added successfully!')
            return redirect('manage_academic_announcements')
    else:
        form = AcademicAnnouncementForm()
    return render(request, 'main/add_academic_announcement.html', {'form': form})

@login_required
@user_passes_test(is_academic_admin)
def edit_academic_announcement(request, pk):
    announcement = get_object_or_404(AcademicAnnouncement, pk=pk)
    if request.method == 'POST':
        form = AcademicAnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement updated successfully!')
            return redirect('manage_academic_announcements')
    else:
        form = AcademicAnnouncementForm(instance=announcement)
    return render(request, 'main/edit_academic_announcement.html', {'form': form, 'announcement': announcement})

@login_required
@user_passes_test(is_academic_admin)
def delete_academic_announcement(request, pk):
    announcement = get_object_or_404(AcademicAnnouncement, pk=pk)
    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Announcement deleted successfully!')
        return redirect('manage_academic_announcements')
    return render(request, 'main/delete_academic_announcement.html', {'announcement': announcement})

# --- Course Catalogs ---
@login_required
@user_passes_test(is_academic_admin)
def manage_course_catalogs(request):
    catalogs = CourseCatalog.objects.all().order_by('-created_at')
    return render(request, 'main/manage_course_catalogs.html', {'catalogs': catalogs})

@login_required
@user_passes_test(is_academic_admin)
def add_course_catalog(request):
    if request.method == 'POST':
        form = CourseCatalogForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course catalog added successfully!')
            return redirect('manage_course_catalogs')
    else:
        form = CourseCatalogForm()
    return render(request, 'main/add_course_catalog.html', {'form': form})

@login_required
@user_passes_test(is_academic_admin)
def edit_course_catalog(request, pk):
    catalog = get_object_or_404(CourseCatalog, pk=pk)
    if request.method == 'POST':
        form = CourseCatalogForm(request.POST, request.FILES, instance=catalog)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course catalog updated successfully!')
            return redirect('manage_course_catalogs')
    else:
        form = CourseCatalogForm(instance=catalog)
    return render(request, 'main/edit_course_catalog.html', {'form': form, 'catalog': catalog})

@login_required
@user_passes_test(is_academic_admin)
def delete_course_catalog(request, pk):
    catalog = get_object_or_404(CourseCatalog, pk=pk)
    if request.method == 'POST':
        catalog.delete()
        messages.success(request, 'Course catalog deleted successfully!')
        return redirect('manage_course_catalogs')
    return render(request, 'main/delete_course_catalog.html', {'catalog': catalog})

# --- Academic Calendars ---
@login_required
@user_passes_test(is_academic_admin)
def manage_academic_calendars(request):
    calendars = AcademicCalendar.objects.all().order_by('-created_at')
    return render(request, 'main/manage_academic_calendars.html', {'calendars': calendars})

@login_required
@user_passes_test(is_academic_admin)
def add_academic_calendar(request):
    if request.method == 'POST':
        form = AcademicCalendarForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Academic calendar added successfully!')
            return redirect('manage_academic_calendars')
    else:
        form = AcademicCalendarForm()
    return render(request, 'main/add_academic_calendar.html', {'form': form})

@login_required
@user_passes_test(is_academic_admin)
def edit_academic_calendar(request, pk):
    calendar = get_object_or_404(AcademicCalendar, pk=pk)
    if request.method == 'POST':
        form = AcademicCalendarForm(request.POST, request.FILES, instance=calendar)
        if form.is_valid():
            form.save()
            messages.success(request, 'Academic calendar updated successfully!')
            return redirect('manage_academic_calendars')
    else:
        form = AcademicCalendarForm(instance=calendar)
    return render(request, 'main/edit_academic_calendar.html', {'form': form, 'calendar': calendar})

@login_required
@user_passes_test(is_academic_admin)
def delete_academic_calendar(request, pk):
    calendar = get_object_or_404(AcademicCalendar, pk=pk)
    if request.method == 'POST':
        calendar.delete()
        messages.success(request, 'Academic calendar deleted successfully!')
        return redirect('manage_academic_calendars')
    return render(request, 'main/delete_academic_calendar.html', {'calendar': calendar})

def is_teacher(user):
    return user.is_authenticated and (
        hasattr(user, 'staff_profile') and 
        user.staff_profile.position == 'Teacher'
    )

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Q
from main.models import Result  # Adjust as needed
from main.models import Subject  # For subject dropdown
from django.utils.datastructures import MultiValueDictKeyError

@login_required
@user_passes_test(is_teacher)
def teacher_result_dashboard(request):
    teacher = request.user.staff_profile
    qs = Result.objects.filter(teacher=teacher)

    # Filters
    query = request.GET.get('q', '')
    subject_id = request.GET.get('subject')
    status = request.GET.get('status')
    term = request.GET.get('term')

    if query:
        qs = qs.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(subject__name__icontains=query) |
            Q(week_number__icontains=query)
        )

    if subject_id and subject_id != 'all':
        qs = qs.filter(subject_id=subject_id)

    if status == 'approved':
        qs = qs.filter(is_approved=True)
    elif status == 'pending':
        qs = qs.filter(is_approved=False)

    if term and term != 'all':
        qs = qs.filter(term=term)

    subjects = Subject.objects.filter(result__teacher=teacher).distinct()
    terms = qs.values_list('term', flat=True).distinct()

    context = {
        'results': qs.order_by('week_number'),
        'subjects': subjects,
        'terms': terms,
        'selected_subject': subject_id,
        'selected_status': status,
        'selected_term': term,
        'query': query,
    }
    return render(request, 'academics/teacher_result_dashboard.html', context)


    
@login_required
@user_passes_test(is_teacher)
def add_result(request):
    teacher = request.user.staff_profile

    if request.method == 'POST':
        form = WeeklyResultForm(request.POST, teacher=teacher)
        if form.is_valid():
            result = form.save(commit=False)
            result.teacher = teacher
            result.save()

            if 'save_add_another' in request.POST:
                messages.success(request, 'Weekly result saved. You can add another one.')
                return redirect('add_result')  # Redirect to the same form
            else:
                messages.success(request, 'Weekly result saved - pending approval.')
                return redirect('teacher_result_dashboard')
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = WeeklyResultForm(teacher=teacher)

    return render(request, 'academics/add_result.html', {
        'form': form,
        'teacher': teacher
    })


@login_required
@user_passes_test(is_teacher)
def edit_result(request, pk):
    teacher = request.user.staff_profile
    result = get_object_or_404(Result, pk=pk, teacher=teacher)
    
    if request.method == 'POST':
        form = WeeklyResultForm(request.POST, instance=result)
        if form.is_valid():
            if result.is_approved:
                # Reset approval on edit
                result.is_approved = False
                result.approved_by = None
                result.date_approved = None
            form.save()
            messages.success(request, 'Result updated successfully! It will need re-approval if previously approved.')
            return redirect('teacher_result_dashboard')
    else:
        form = WeeklyResultForm(instance=result)
    
    return render(request, 'academics/edit_result.html', {
        'form': form,
        'result': result
    })


@login_required
@user_passes_test(is_teacher)
def delete_result(request, pk):
    teacher = request.user.staff_profile
    result = get_object_or_404(Result, pk=pk, teacher=teacher)
    
    if request.method == 'POST':
        result.delete()
        messages.success(request, 'Result deleted successfully!')
        return redirect('teacher_result_dashboard')
    
    return render(request, 'academics/delete_result.html', {'result': result})


@login_required
@user_passes_test(is_academic_admin)
def admin_result_dashboard(request):
    status = request.GET.get('status', None)
    
    # Base queryset
    results = Result.objects.all()
    
    # Filter based on status
    if status == 'pending':
        results = results.filter(is_approved=False)
        title = "Pending Approval Results"
    elif status == 'approved':
        results = results.filter(is_approved=True)
        title = "Approved Results"
    else:
        title = "All Results"
    
    # Order by most recent first (using date_approved for approved, id for pending)
    if status == 'approved':
        results = results.order_by('-date_approved')
    else:
        results = results.order_by('-id')  # or another field you want to sort by
    
    # Pagination
    paginator = Paginator(results, 25)  # Show 25 results per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'academics/admin_result_dashboard.html', {
        'results': page_obj,
        'title': title,
        'is_paginated': paginator.num_pages > 1,
    })

@login_required
@user_passes_test(is_academic_admin)
def review_result(request, pk):
    result = get_object_or_404(Result, pk=pk)
    
    if request.method == 'POST':
        form = ResultApprovalForm(request.POST, instance=result)
        if form.is_valid():
            result = form.save(commit=False)
            if result.is_approved:
                result.approved_by = request.user
                result.date_approved = timezone.now()
                result.save()
                
                # Send push notification to parent
                if result.student.parent and result.student.parent.user:
                    send_push_notification(
                        user=result.student.parent.user,
                        title="New Results Available",
                        message=f"Results for {result.student} in {result.subject} are now available",
                        url=reverse('parent_view_results')
                    )
                
                messages.success(request, 'Result approved successfully!')
            else:
                result.save()
                messages.success(request, 'Result approval status updated!')
            return redirect('admin_result_dashboard')
    else:
        form = ResultApprovalForm(instance=result)
    
    return render(request, 'academics/review_result.html', {
        'form': form,
        'result': result
    })

@login_required
@user_passes_test(is_academic_admin)
def bulk_approve_results(request):
    if request.method == 'POST':
        result_ids = request.POST.getlist('result_ids')
        results = Result.objects.filter(id__in=result_ids, is_approved=False)
        
        updated = results.update(
            is_approved=True,
            approved_by=request.user,
            date_approved=timezone.now()
        )
        
        # Send push notifications for bulk approval
        if results.exists():
            first_result = results.first()
            parents = User.objects.filter(
                parent_profile__students__results__in=results
            ).distinct()
            
            for parent in parents:
                send_push_notification(
                    user=parent,
                    title="New Results Available",
                    message=f"Results for {first_result.get_term_display()} term are now available",
                    url=reverse('parent_view_results')
                )
        
        messages.success(request, f'Successfully approved {updated} results!')
        return redirect('admin_result_dashboard')
    
    pending_results = Result.objects.filter(is_approved=False).order_by('teacher', 'student')
    return render(request, 'academics/bulk_approve_results.html', {
        'pending_results': pending_results
    })

@login_required
def parent_view_results(request):
    # Get all students associated with this parent (by email)
    students = Student.objects.filter(parent_email=request.user.email)
    
    if not students.exists():
        raise PermissionDenied
    
    # Get all approved results for these students
    results = Result.objects.filter(
        student__in=students,
        is_approved=True
    ).order_by('-academic_year', 'term', 'subject')
    
    # Group results by student, then by academic year and term
    results_by_student = {}
    for student in students:
        student_results = results.filter(student=student)
        results_by_year_term = {}
        
        for result in student_results:
            key = f"{result.academic_year} - {result.get_term_display()}"
            if key not in results_by_year_term:
                results_by_year_term[key] = []
            results_by_year_term[key].append(result)
        
        results_by_student[student] = results_by_year_term
    
    return render(request, 'academics/parent_view_results.html', {
        'results_by_student': results_by_student
    })


@login_required
@user_passes_test(is_teacher)
def teacher_classes(request):
    teacher = request.user.staff_profile
    classes_taught = SchoolClass.objects.filter(teacher=teacher)
    return render(request, 'academics/teacher_classes.html', {
        'classes_taught': classes_taught
    })


@login_required
@user_passes_test(is_teacher)
def teacher_gradebook(request):
    teacher = request.user.staff_profile
    results = Result.objects.filter(teacher=teacher, is_approved=True)
    return render(request, 'academics/teacher_gradebook.html', {
        'results': results
    })


from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from collections import defaultdict
from .models import Student, Result

def calculate_division(student, term_results):
    """Calculate division based on Tanzanian system."""
    level_name = student.level.name.lower()
    is_a_level = 'form v' in level_name or 'form vi' in level_name

    # Group results by subject and calculate average total_score
    subject_averages = defaultdict(list)
    for result in term_results:
        subject_averages[result.subject].append(result.total_score)

    # Calculate average per subject and map to points
    subject_points = []
    for subject, scores in subject_averages.items():
        avg_score = sum(scores) / len(scores)
        if avg_score >= 81:
            points = 1  # A
        elif avg_score >= 70:
            points = 2  # B
        elif avg_score >= 69:
            points = 3  # C
        elif avg_score >= 59:
            points = 4  # D
        else:
            points = 9  # F
        subject_points.append(points)

    # Sort points and select best subjects
    subject_points.sort()
    if is_a_level:
        # For Form V-VI, take best 3 subjects
        relevant_points = subject_points[:3] if len(subject_points) >= 3 else subject_points
        total_points = sum(relevant_points)
        if len(subject_points) > 4:
            return "Invalid: More than 4 subjects", total_points
        if 3 <= total_points <= 9:
            return "Division I", total_points
        elif 10 <= total_points <= 12:
            return "Division II", total_points
        elif 13 <= total_points <= 15:
            return "Division III", total_points
        elif 16 <= total_points <= 18:
            return "Division IV", total_points
        else:
            return "Division 0", total_points
    else:
        # For Form I-IV, take best 7 subjects
        relevant_points = subject_points[:7] if len(subject_points) >= 7 else subject_points
        total_points = sum(relevant_points)
        if 7 <= total_points <= 17:
            return "Division I", total_points
        elif 18 <= total_points <= 24:
            return "Division II", total_points
        elif 25 <= total_points <= 31:
            return "Division III", total_points
        elif 32 <= total_points <= 38:
            return "Division IV", total_points
        else:
            return "Division 0", total_points

@login_required
def parent_view_results(request):
    try:
        parent = request.user.parent_profile
    except Parent.DoesNotExist:
        raise PermissionDenied("No parent profile found for this account.")

    students = Student.objects.filter(parent=parent)
    if not students.exists():
        raise PermissionDenied("No students associated with this parent account.")

    results = Result.objects.filter(
        student__in=students,
        is_approved=True
    ).order_by('-academic_year', 'term', 'week_number')

    results_by_student = {}
    for student in students:
        student_results = results.filter(student=student)
        results_by_year_term = defaultdict(list)

        for result in student_results:
            year_term = f"{result.academic_year} - {result.get_term_display()}"
            results_by_year_term[year_term].append(result)

        structured_results = {}
        for year_term, term_results in results_by_year_term.items():
            weeks = defaultdict(list)
            for result in term_results:
                weeks[result.week_number].append(result)

            weekly_data = {}
            for week_number, weekly_results in weeks.items():
                week_division = calculate_division(student, weekly_results)
                weekly_data[week_number] = {
                    'results': weekly_results,
                    'division': week_division
                }

            # --- Monthly Estimation ---
            monthly_estimations = []
            for i in range(0, 15, 4):  # every 4 weeks (0,4,8,12)
                monthly_total_scores = []
                for week in range(i + 1, min(i + 5, 16)):  # 1-4, 5-8, 9-12, 13-15
                    if week in weekly_data:
                        for r in weekly_data[week]['results']:
                            if r.total_score is not None:
                                monthly_total_scores.append(r.total_score)

                if monthly_total_scores:
                    avg = round(sum(monthly_total_scores) / len(monthly_total_scores), 2)
                else:
                    avg = None

                monthly_estimations.append({
                    'month': f"Month {(i // 4) + 1}",
                    'average_score': avg
                })

            structured_results[year_term] = {
                'weeks': weekly_data,
                'monthly_estimations': monthly_estimations
            }

        results_by_student[student] = structured_results

    return render(request, 'academics/parent_view_results.html', {
        'results_by_student': results_by_student
    })


from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def filter_students_by_level(request):
    level_id = request.GET.get('level')
    if not level_id:
        return JsonResponse({'error': 'Level ID is required'}, status=400)
    
    try:
        # Get currently selected student IDs from the request
        selected_ids = request.GET.getlist('selected[]', [])
        selected_ids = [int(id) for id in selected_ids if id.isdigit()]
        
        students = Student.objects.filter(level_id=level_id).order_by('last_name', 'first_name')
        student_options = [
            {
                'id': s.id, 
                'text': f"{s.last_name}, {s.first_name} ({s.admission_number})",
                'selected': s.id in selected_ids
            }
            for s in students
        ]
        return JsonResponse({'students': student_options})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)



@require_GET
def filter_students_by_class(request):
    class_id = request.GET.get('school_class')
    if not class_id:
        return JsonResponse({'error': 'Class ID is required'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id)
        students = school_class.students.all().order_by('last_name', 'first_name')
        subjects = Subject.objects.filter(level=school_class.level)
        
        student_options = [{
            'id': s.id, 
            'text': f"{s.last_name}, {s.first_name} ({s.admission_number})"
        } for s in students]
        
        subject_options = [{
            'id': s.id,
            'text': f"{s.name} ({s.code})"
        } for s in subjects]
        
        return JsonResponse({
            'students': student_options,
            'subjects': subject_options
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




@require_GET
@login_required
def get_class_students(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'error': 'Class ID is required'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id)
        students = school_class.students.all().order_by('last_name', 'first_name')
        
        student_options = [{
            'id': s.id, 
            'text': f"{s.last_name}, {s.first_name} ({s.admission_number})"
        } for s in students]
        
        return JsonResponse({'students': student_options})
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def get_class_subjects(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'error': 'Class ID is required'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id)
        subjects = Subject.objects.filter(level=school_class.level).order_by('name')
        
        subject_options = [{
            'id': s.id,
            'text': f"{s.name} ({s.code})"
        } for s in subjects]
        
        return JsonResponse({'subjects': subject_options})
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




def get_student_results(student):
    results = Result.objects.filter(student=student, is_approved=True).order_by('-academic_year', 'term', 'week_number')
    results_by_year_term = {}
    for result in results:
        year_term = f"{result.academic_year} - {result.get_term_display()}"
        if year_term not in results_by_year_term:
            # Assuming calculate_division is defined elsewhere in your code
            division = calculate_division(student, results.filter(academic_year=result.academic_year, term=result.term))
            results_by_year_term[year_term] = {'weeks': {}, 'division': division}
        week_number = result.week_number
        if week_number not in results_by_year_term[year_term]['weeks']:
            results_by_year_term[year_term]['weeks'][week_number] = []
        results_by_year_term[year_term]['weeks'][week_number].append(result)
    return results_by_year_term

@login_required
def download_result_pdf(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if student.parent != request.user.parent_profile:
        raise PermissionDenied
    results_by_year_term = get_student_results(student)
    context = {
        'student': student,
        'results_by_year_term': results_by_year_term,
    }
    html_string = render_to_string('academics/result_pdf.html', context)
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="result_{student.id}.pdf"'
    return response



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pywebpush import webpush, WebPushException
import json
from django.conf import settings

@csrf_exempt
def save_subscription(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            PushSubscription.objects.create(
                user=request.user,
                subscription=data
            )
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'}, status=400)

import logging
from django.conf import settings
from pywebpush import webpush, WebPushException
import json

logger = logging.getLogger(__name__)

def send_push_notification(user, title, message, url):
    """
    Enhanced push notification sender with comprehensive logging
    """
    # Initial log
    logger.info(f"Attempting to send push notification to user {user.id} ({user.username})")
    logger.debug(f"Notification details - Title: '{title}', Message: '{message}', URL: '{url}'")

    # Get all subscriptions for the user
    subscriptions = PushSubscription.objects.filter(user=user)
    subscription_count = subscriptions.count()
    logger.info(f"Found {subscription_count} push subscription(s) for user {user.id}")

    if subscription_count == 0:
        logger.warning("No push subscriptions found for this user")
        return False

    successful_sends = 0
    failed_sends = 0

    for sub in subscriptions:
        try:
            # Log subscription details (sensitive info redacted)
            logger.debug(f"Processing subscription ID {sub.id}")
            logger.debug(f"Subscription endpoint: {sub.subscription.get('endpoint', '')[0:50]}...")
            logger.debug(f"Created at: {sub.created_at}")

            # Prepare notification payload
            payload = {
                'title': title,
                'body': message,
                'url': url,
                'icon': '/static/images/Ahmes.PNG',  # Ensure this matches your service worker
                'vibrate': [200, 100, 200]
            }
            logger.debug("Notification payload prepared", extra={'payload': payload})

            # Webpush configuration
            vapid_config = {
                'vapid_private_key': settings.VAPID_PRIVATE_KEY[:10] + '...' if settings.VAPID_PRIVATE_KEY else None,
                'vapid_claims': settings.VAPID_CLAIMS
            }
            logger.debug("VAPID configuration", extra={'vapid_config': vapid_config})

            # Attempt to send notification
            logger.info(f"Sending push to subscription ID {sub.id}")
            webpush(
                subscription_info=sub.subscription,
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=settings.VAPID_CLAIMS
            )
            successful_sends += 1
            logger.info(f"Successfully sent push to subscription ID {sub.id}")

        except WebPushException as e:
            failed_sends += 1
            error_details = {
                'error': str(e),
                'status_code': getattr(e, 'response', {}).status_code if hasattr(e, 'response') else None,
                'subscription_id': sub.id,
                'user_id': user.id
            }
            logger.error("WebPushException occurred", extra=error_details)

            # Handle expired subscriptions
            if hasattr(e, 'response') and e.response.status_code == 410:
                logger.warning(f"Deleting expired subscription ID {sub.id}")
                sub.delete()

        except json.JSONEncodeError as e:
            failed_sends += 1
            logger.error(f"JSON encoding error: {str(e)}")
            
        except Exception as e:
            failed_sends += 1
            logger.exception(f"Unexpected error sending push notification: {str(e)}")

    # Final summary
    logger.info(
        f"Notification dispatch complete - Successful: {successful_sends}, Failed: {failed_sends}",
        extra={
            'user_id': user.id,
            'successful': successful_sends,
            'failed': failed_sends,
            'total_subscriptions': subscription_count
        }
    )

    return successful_sends > 0





from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from .models import ActivityLog, User
from datetime import datetime

@login_required
@user_passes_test(lambda u: u.is_admin)
def activity_log(request):
    # Get filter parameters from request
    action = request.GET.get('action', '')
    user_id = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with base queryset
    activities = ActivityLog.objects.all().select_related('user').order_by('-timestamp')
    
    # Apply filters
    if action:
        activities = activities.filter(action=action)
    if user_id:
        activities = activities.filter(user_id=user_id)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all available users who have activities
    users = User.objects.filter(activitylog__isnull=False).distinct()
    
    # Get the filtered user for display
    filtered_user = None
    if user_id:
        try:
            filtered_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass
    
    context = {
        'page_obj': page_obj,
        'actions': ActivityLog.ACTION_CHOICES,
        'users': users,
        'selected_action': action,
        'selected_user': user_id,
        'filtered_user': filtered_user,  # Add this
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'main/activity_log.html', context)



from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from .models import InventoryCategory, InventoryItem, InventoryTransaction

def is_admin(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_admin)
def inventory_dashboard(request):
    categories = InventoryCategory.objects.all()
    total_items = InventoryItem.objects.count()
    low_stock_items = InventoryItem.objects.filter(status='LOW_STOCK').count()
    out_of_stock_items = InventoryItem.objects.filter(status='OUT_OF_STOCK').count()
    
    # Calculate total inventory value
    total_value_result = InventoryItem.objects.aggregate(total=Sum('total_value'))
    total_value = total_value_result['total'] or Decimal('0.00')
    
    context = {
        'categories': categories,
        'total_items': total_items,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'total_value': f"{total_value:,.0f}",  # Format with commas, no decimals
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def inventory_items(request, category_id=None):
    category = None
    if category_id:
        category = get_object_or_404(InventoryCategory, id=category_id)
        items = InventoryItem.objects.filter(category=category)
    else:
        items = InventoryItem.objects.all()
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    # Add distinct() to prevent duplicates and order by name
    items = items.distinct().order_by('name')
    
    context = {
        'items': items,
        'category': category,
        'categories': InventoryCategory.objects.all(),
    }
    return render(request, 'inventory/items.html', context)

@login_required
@user_passes_test(is_admin)
def add_inventory_item(request):
    if request.method == 'POST':
        # Process form data and create new inventory item
        name = request.POST.get('name')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        quantity = int(request.POST.get('quantity', 0))
        unit = request.POST.get('unit', 'pcs')
        unit_price = Decimal(request.POST.get('unit_price', 0))
        minimum_stock = int(request.POST.get('minimum_stock', 5))
        location = request.POST.get('location')
        supplier = request.POST.get('supplier')
        notes = request.POST.get('notes')
        
        category = get_object_or_404(InventoryCategory, id=category_id)
        
        item = InventoryItem(
            name=name,
            description=description,
            category=category,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
            minimum_stock=minimum_stock,
            location=location,
            supplier=supplier,
            notes=notes,
            created_by=request.user,
            last_updated_by=request.user
        )
        item.save()
        
        # Create initial transaction if quantity > 0
        if quantity > 0:
            transaction = InventoryTransaction(
                item=item,
                transaction_type='IN',
                quantity=quantity,
                unit_price=unit_price,
                notes='Initial stock',
                created_by=request.user
            )
            transaction.save()
        
        messages.success(request, f'Item "{name}" added successfully!')
        return redirect('inventory_items')
    
    categories = InventoryCategory.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'inventory/add_item.html', context)

@login_required
@user_passes_test(is_admin)
def edit_inventory_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        # Process form data and update inventory item
        item.name = request.POST.get('name')
        item.description = request.POST.get('description')
        category_id = request.POST.get('category')
        item.unit = request.POST.get('unit', 'pcs')
        item.unit_price = Decimal(request.POST.get('unit_price', 0))
        item.minimum_stock = int(request.POST.get('minimum_stock', 5))
        item.location = request.POST.get('location')
        item.supplier = request.POST.get('supplier')
        item.notes = request.POST.get('notes')
        item.last_updated_by = request.user
        
        if category_id:
            category = get_object_or_404(InventoryCategory, id=category_id)
            item.category = category
        
        item.save()
        
        messages.success(request, f'Item "{item.name}" updated successfully!')
        return redirect('inventory_items')
    
    categories = InventoryCategory.objects.all()
    context = {
        'item': item,
        'categories': categories,
    }
    return render(request, 'inventory/edit_item.html', context)

@login_required
@user_passes_test(is_admin)
def delete_inventory_item(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        item_name = item.name
        item.delete()
        messages.success(request, f'Item "{item_name}" deleted successfully!')
        return redirect('inventory_items')
    
    context = {
        'item': item,
    }
    return render(request, 'inventory/delete_item.html', context)

@login_required
@user_passes_test(is_admin)
def inventory_transactions(request, item_id=None):
    if item_id:
        item = get_object_or_404(InventoryItem, id=item_id)
        transactions = InventoryTransaction.objects.filter(item=item)
    else:
        item = None
        transactions = InventoryTransaction.objects.all()
    
    transactions = transactions.order_by('-created_at')
    
    context = {
        'transactions': transactions,
        'item': item,
    }
    return render(request, 'inventory/transactions.html', context)

@login_required
@user_passes_test(is_admin)
def add_inventory_transaction(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        transaction_type = request.POST.get('transaction_type')
        quantity = int(request.POST.get('quantity', 0))
        unit_price = request.POST.get('unit_price')
        notes = request.POST.get('notes')
        
        if unit_price:
            unit_price = Decimal(unit_price)
        else:
            unit_price = item.unit_price
        
        # Create transaction
        transaction = InventoryTransaction(
            item=item,
            transaction_type=transaction_type,
            quantity=quantity if transaction_type == 'IN' else -quantity,
            unit_price=unit_price,
            notes=notes,
            created_by=request.user
        )
        transaction.save()
        
        # Update item quantity based on transaction
        if transaction_type == 'IN':
            item.quantity += quantity
        elif transaction_type == 'OUT':
            item.quantity = max(0, item.quantity - quantity)  # Prevent negative quantities
        elif transaction_type == 'ADJUST':
            item.quantity = quantity
            
        item.save()  # This will recalculate total_value correctly
        
        messages.success(request, f'Transaction recorded for "{item.name}"!')
        return redirect('inventory_transactions', item_id=item.id)
    
    context = {
        'item': item,
    }
    return render(request, 'inventory/add_transaction.html', context)