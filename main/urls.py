from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import CustomLoginView, register, verify_email, inbox, chat, logout_view, get_conversations,mark_messages_read, get_new_messages

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('staff/', views.staff, name='staff'),
    path('contact/', views.contact, name='contact'),
    
    # Authentication
    path('ad/login/', views.admin_login, name='admin_login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Admin dashboard
    path('ad/board/', views.admin_dashboard, name='admin_dashboard'),
    
    # Student management
    path('ad/students/', views.manage_students, name='manage_students'),
    path('ad/students/add/', views.add_student, name='add_student'),
    path('ad/students/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('ad/students/delete/<int:pk>/', views.delete_student, name='delete_student'),
    
    # Staff management
    path('ad/staff/', views.manage_staff, name='manage_staff'),
    path('ad/staff/add/', views.add_staff, name='add_staff'),
    path('ad/staff/edit/<int:pk>/', views.edit_staff, name='edit_staff'),
    path('ad/staff/delete/<int:pk>/', views.delete_staff, name='delete_staff'),

    # News management
    path('ad/news/', views.manage_news, name='manage_news'),
    path('ad/news/add/', views.add_news, name='add_news'),
    path('ad/news/edit/<int:pk>/', views.edit_news, name='edit_news'),
    path('ad/news/delete/<int:pk>/', views.delete_news, name='delete_news'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),


    # Comment management
    path('ad/comments/', views.manage_comments, name='manage_comments'),
    path('ad/comments/approve/<int:pk>/', views.approve_comment, name='approve_comment'),
    path('ad/comments/delete/<int:pk>/', views.delete_comment, name='delete_comment'),

    # Gallery management
    path('ad/manage-gallery/', views.manage_gallery, name='manage_gallery'),
    path('ad/gallery/add/', views.add_gallery, name='add_gallery'),
    path('ad/gallery/edit/<int:pk>/', views.edit_gallery, name='edit_gallery'),
    path('ad/gallery/delete/<int:pk>/', views.delete_gallery, name='delete_gallery'),
    path('gallery/', views.gallery, name='gallery'),

    #Chats
    path('login/tochat/', CustomLoginView.as_view(), name='login'),
    path('register/', register, name='register'),
    path('verify-email/', verify_email, name='verify_email'),
    path('inbox/', inbox, name='inbox'),
    path('chat/<int:conversation_id>/', chat, name='chat'),
    path('logout/', logout_view, name='out'),
    path('messages/mark_read/', views.mark_messages_read, name='mark_messages_read'),
    path('conversations/<int:conversation_id>/messages/', get_new_messages, name='get_new_messages'),
    path('api/conversations/', get_conversations, name='get_conversations'),

    # Under development page
    path('under-development/', views.under_development, name='under_development'),
    path('conversations/typing/', views.handle_typing, name='handle_typing'),
    path('conversations/<int:conversation_id>/typing-status/', views.get_typing_status, name='typing_status'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)