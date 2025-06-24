from django.urls import path
from . import views

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

    # Comment management
    path('ad/comments/', views.manage_comments, name='manage_comments'),
    path('ad/comments/approve/<int:pk>/', views.approve_comment, name='approve_comment'),
    path('ad/comments/delete/<int:pk>/', views.delete_comment, name='delete_comment'),
]