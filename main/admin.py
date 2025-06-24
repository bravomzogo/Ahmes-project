from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Campus, Level, Student, StaffMember, News, Comment

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_admin', 'is_staff_member', 'is_staff')
    list_filter = ('is_admin', 'is_staff_member')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin', 'is_staff_member', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'admission_number', 'campus', 'level', 'admission_date')
    list_filter = ('campus', 'level')
    search_fields = ('first_name', 'last_name', 'admission_number')

class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'position', 'campus', 'joined_date')
    list_filter = ('position', 'campus')
    search_fields = ('first_name', 'last_name')

class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_date', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'author_name', 'created_at', 'is_approved')
    list_filter = ('is_approved',)
    search_fields = ('content', 'author_name', 'author_email')

admin.site.register(User, CustomUserAdmin)
admin.site.register(Campus)
admin.site.register(Level)
admin.site.register(Student, StudentAdmin)
admin.site.register(StaffMember, StaffMemberAdmin)
admin.site.register(News, NewsAdmin)
admin.site.register(Comment, CommentAdmin)