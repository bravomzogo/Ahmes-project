from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Campus,
    Level,
    Student,
    StaffMember,
    News,
    Comment,
    Gallery,
    EmailVerification,
    Conversation,
    Message,
    YouTubeVideo,
    SchoolClass,
    CourseCatalog,
    AcademicCalendar,
    AcademicAnnouncement
)

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_admin', 'is_staff_member', 'is_online')
    list_filter = ('is_admin', 'is_staff_member', 'is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin', 'is_staff_member', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'last_activity')}),
    )

admin.site.register(User, CustomUserAdmin)

# Other model registrations
@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location')

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'admission_number', 'campus', 'level')
    list_filter = ('campus', 'level', 'gender')
    search_fields = ('first_name', 'last_name', 'admission_number')
    raw_id_fields = ('user',)

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'position', 'campus', 'specialization')
    list_filter = ('position', 'campus')
    search_fields = ('first_name', 'last_name', 'position')
    raw_id_fields = ('user',)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_date', 'is_published')
    list_filter = ('is_published', 'published_date')
    search_fields = ('title', 'content')
    raw_id_fields = ('author',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author_name', 'content')

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'author', 'published_date', 'is_published')
    list_filter = ('media_type', 'is_published')
    search_fields = ('title', 'description')
    raw_id_fields = ('author',)

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'activation_code_expires')
    search_fields = ('user__username', 'user__email', 'code')
    raw_id_fields = ('user',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at')
    filter_horizontal = ('participants',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('content',)
    raw_id_fields = ('conversation', 'sender')

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'video_id', 'published_at', 'is_featured')
    list_filter = ('is_featured', 'published_at')
    search_fields = ('title', 'description', 'video_id')

@admin.register(SchoolClass)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'teacher', 'academic_year', 'student_count')
    list_filter = ('level', 'academic_year')
    search_fields = ('name',)
    raw_id_fields = ('teacher',)
    filter_horizontal = ('students',)

@admin.register(CourseCatalog)
class CourseCatalogAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    list_filter = ('is_active', 'academic_year')
    search_fields = ('title',)

@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    list_filter = ('is_active', 'academic_year')
    search_fields = ('title',)

@admin.register(AcademicAnnouncement)
class AcademicAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_published')
    list_filter = ('is_published', 'date')
    search_fields = ('title', 'content')