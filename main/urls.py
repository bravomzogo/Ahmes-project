from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import (
    CustomLoginView, add_academic_announcement, add_academic_calendar, add_class, add_course_catalog, manage_academic_announcements, manage_academic_calendars, manage_classes, manage_course_catalogs, parent_view_results, register, verify_email, inbox, chat, logout_view, 
    get_conversations, mark_messages_read, get_new_messages, 
    StudentLoginView, TeacherLoginView, ParentLoginView, AcademicAdminLoginView,
    student_dashboard, teacher_dashboard, parent_dashboard, academic_admin_dashboard
)



urlpatterns = [
    # Existing URLs (unchanged)
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('staff/', views.staff, name='staff'),
    path('contact/', views.contact, name='contact'),
    path('ad/login/', views.admin_login, name='admin_login'),
    path('logout/', views.custom_logout, name='logout'),
    path('ad/board/', views.admin_dashboard, name='admin_dashboard'),
    path('ad/students/', views.manage_students, name='manage_students'),
    path('ad/students/add/', views.add_student, name='add_student'),
    path('ad/students/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('ad/students/delete/<int:pk>/', views.delete_student, name='delete_student'),
    path('ad/staff/', views.manage_staff, name='manage_staff'),
    path('ad/staff/add/', views.add_staff, name='add_staff'),
    path('ad/staff/edit/<int:pk>/', views.edit_staff, name='edit_staff'),
    path('ad/staff/delete/<int:pk>/', views.delete_staff, name='delete_staff'),
    path('ad/news/', views.manage_news, name='manage_news'),
    path('ad/news/add/', views.add_news, name='add_news'),
    path('ad/news/edit/<int:pk>/', views.edit_news, name='edit_news'),
    path('ad/news/delete/<int:pk>/', views.delete_news, name='delete_news'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),
    path('ad/comments/', views.manage_comments, name='manage_comments'),
    path('ad/comments/approve/<int:pk>/', views.approve_comment, name='approve_comment'),
    path('ad/comments/delete/<int:pk>/', views.delete_comment, name='delete_comment'),
    path('ad/manage-gallery/', views.manage_gallery, name='manage_gallery'),
    path('ad/gallery/add/', views.add_gallery, name='add_gallery'),
    path('ad/gallery/edit/<int:pk>/', views.edit_gallery, name='edit_gallery'),
    path('ad/gallery/delete/<int:pk>/', views.delete_gallery, name='delete_gallery'),
    path('gallery/', views.gallery, name='gallery'),
    path('login/tochat/', CustomLoginView.as_view(), name='login'),
    path('register/', register, name='register'),
    path('verify-email/', verify_email, name='verify_email'),
    path('inbox/', inbox, name='inbox'),
    path('chat/<int:conversation_id>/', chat, name='chat'),
    path('logout/', logout_view, name='out'),
    path('messages/mark_read/', views.mark_messages_read, name='mark_messages_read'),
    path('conversations/<int:conversation_id>/messages/', get_new_messages, name='get_new_messages'),
    path('api/conversations/', get_conversations, name='get_conversations'),
    path('under-development/', views.under_development, name='under_development'),
    path('conversations/typing/', views.handle_typing, name='handle_typing'),
    path('conversations/<int:conversation_id>/typing-status/', views.get_typing_status, name='typing_status'),
    path('ahmes-tv/', views.ahmes_tv, name='ahmes_tv'),
    path('academics/', views.academic_services, name='academics_service'),
    path('academics/student/login/', StudentLoginView.as_view(), name='student_login'),
    path('academics/teacher/login/', TeacherLoginView.as_view(), name='teacher_login'),
    path('academics/parent/login/', ParentLoginView.as_view(), name='parent_login'),
    path('academics/admin/login/', AcademicAdminLoginView.as_view(), name='academic_admin_login'),
    path('academics/student/dashboard/', student_dashboard, name='student_dashboard'),
    path('academics/teacher/dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('academics/parent/dashboard/', parent_dashboard, name='parent_dashboard'),
    path('academics/admin/dashboard/', academic_admin_dashboard, name='academic_admin_dashboard'),

   # New URLs for academic management
path('ad/classes/', manage_classes, name='manage_classes'),
path('ad/classes/add/', add_class, name='add_class'),
path('ad/classes/edit/<int:pk>/', views.edit_class, name='edit_class'),
path('ad/classes/delete/<int:pk>/', views.delete_class, name='delete_class'),

path('ad/academic-announcements/', manage_academic_announcements, name='manage_academic_announcements'),
path('ad/academic-announcements/add/', add_academic_announcement, name='add_academic_announcement'),
path('ad/academic-announcements/edit/<int:pk>/', views.edit_academic_announcement, name='edit_academic_announcement'),
path('ad/academic-announcements/delete/<int:pk>/', views.delete_academic_announcement, name='delete_academic_announcement'),

path('ad/course-catalogs/', manage_course_catalogs, name='manage_course_catalogs'),
path('ad/course-catalogs/add/', add_course_catalog, name='add_course_catalog'),
path('ad/course-catalogs/edit/<int:pk>/', views.edit_course_catalog, name='edit_course_catalog'),
path('ad/course-catalogs/delete/<int:pk>/', views.delete_course_catalog, name='delete_course_catalog'),
path('parent/results/', parent_view_results, name='parent_view_results'),

path('ad/academic-calendars/', manage_academic_calendars, name='manage_academic_calendars'),
path('ad/academic-calendars/add/', add_academic_calendar, name='add_academic_calendar'),
path('ad/academic-calendars/edit/<int:pk>/', views.edit_academic_calendar, name='edit_academic_calendar'),
path('ad/academic-calendars/delete/<int:pk>/', views.delete_academic_calendar, name='delete_academic_calendar'),

    # Teacher URLs
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/results/', views.teacher_result_dashboard, name='teacher_result_dashboard'),
    path('teacher/results/add/', views.add_result, name='add_result'),
    path('teacher/results/edit/<int:pk>/', views.edit_result, name='edit_result'),
    path('teacher/results/delete/<int:pk>/', views.delete_result, name='delete_result'),
    path('teacher/classes/', views.teacher_classes, name='teacher_classes'),
    path('teacher/gradebook/', views.teacher_gradebook, name='teacher_gradebook'),
    
    # Admin URLs
    path('ad/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('ad/results/', views.admin_result_dashboard, name='admin_result_dashboard'),
    path('ad/results/review/<int:pk>/', views.review_result, name='review_result'),
    path('ad/results/bulk-approve/', views.bulk_approve_results, name='bulk_approve_results'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)