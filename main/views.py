from venv import logger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views import View
from .models import AcademicAnnouncement, AcademicCalendar, Campus, CourseCatalog, Gallery, Level, Parent, PushSubscription, Result, SchoolClass, Student, StaffMember, News, Comment, Subject, User
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

def ahmes_tv(request):
    page = request.GET.get('page', 1)
    search_query = request.GET.get('search', '')
    
    # Base filter to ensure only AHMES-related videos
    videos = YouTubeVideo.objects.filter(
        Q(title__icontains='AHMES') | Q(description__icontains='AHMES')
    )
    
    # Additional search filtering if a query is provided
    if search_query:
        videos = videos.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Order by published date (newest first)
    videos = videos.order_by('-published_at')
    
    # Pagination: 9 videos per page
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

class ParentLoginView(View):
    template_name = 'academics/parent_login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_parent:
                logger.debug(f"Authenticated parent {request.user.username} redirected to dashboard")
                return redirect('parent_dashboard')  # Replace with your parent dashboard URL
            else:
                messages.error(request, 'This page is for parent accounts only.')
                logger.warning(f"Non-parent user {request.user.username} attempted parent login")
                return redirect('home')  # Replace with your home URL
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
                    # Handle "remember me" checkbox
                       # Handle "remember me" checkbox
                    if not request.POST.get('remember'):
                        request.session.set_expiry(0)  # Session expires on browser close
                    else:
                        request.session.set_expiry(1209600)  # 2 weeks
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
    # Check if the user is a parent
    if not request.user.is_parent:
        raise PermissionDenied("This page is for parent accounts only.")

    # Get the Parent object linked to the user
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        raise PermissionDenied("No parent profile found for this account.")

    # Get all students associated with this parent
    students = Student.objects.filter(parent=parent)
    if not students.exists():
        raise PermissionDenied("No students associated with this parent account.")

    return render(request, 'academics/parent_dashboard.html', {
        'students': students
    })

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

@login_required
@user_passes_test(is_teacher)
def teacher_result_dashboard(request):
    qs = Result.objects.filter(teacher=request.user.staff_profile)
    status = request.GET.get('status')
    if status == 'pending':
        qs = qs.filter(is_approved=False)
    elif status == 'approved':
        qs = qs.filter(is_approved=True)
    # monthly estimations: group weeks 1‑4, 5‑8, 9‑12, 13‑15
    from django.db.models import Avg, Q  # Ensure Q is imported here
    monthly = qs.values('student', 'term', 'academic_year').annotate(
        month1=Avg('total_score', filter=Q(week_number__gte=1, week_number__lte=4)),
        month2=Avg('total_score', filter=Q(week_number__gte=5, week_number__lte=8)),
        month3=Avg('total_score', filter=Q(week_number__gte=9, week_number__lte=12)),
        month4=Avg('total_score', filter=Q(week_number__gte=13, week_number__lte=15)),
    )
    context = {'results': qs.order_by('week_number'), 'monthly': monthly}
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
        if avg_score >= 75:
            points = 1  # A
        elif avg_score >= 65:
            points = 2  # B
        elif avg_score >= 55:
            points = 3  # C
        elif avg_score >= 45:
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
    # Get the Parent object linked to the user
    try:
        parent = request.user.parent_profile
    except Parent.DoesNotExist:
        raise PermissionDenied("No parent profile found for this account.")

    # Get all students associated with this parent
    students = Student.objects.filter(parent=parent)
    if not students.exists():
        raise PermissionDenied("No students associated with this parent account.")

    # Get all approved results for these students
    results = Result.objects.filter(
        student__in=students,
        is_approved=True
    ).order_by('-academic_year', 'term', 'week_number')

    # Group results by student, then by year-term, and calculate division
    results_by_student = {}
    for student in students:
        student_results = results.filter(student=student)
        results_by_year_term = defaultdict(list)
        
        # Group by year-term
        for result in student_results:
            year_term = f"{result.academic_year} - {result.get_term_display()}"
            results_by_year_term[year_term].append(result)
        
        # Calculate division and structure results
        structured_results = {}
        for year_term, term_results in results_by_year_term.items():
            division = calculate_division(student, term_results)
            weeks = defaultdict(list)
            for result in term_results:
                weeks[result.week_number].append(result)
            structured_results[year_term] = {
                'weeks': dict(weeks),
                'division': division
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