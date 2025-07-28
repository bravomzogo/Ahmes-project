from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from .models import (
    User, Campus, Level, Student, StaffMember, News, Comment, Gallery,
    EmailVerification, Conversation, Message, YouTubeVideo, SchoolClass,
    CourseCatalog, AcademicCalendar, AcademicAnnouncement, Subject, Result
)

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'is_admin', 'is_staff_member', 'is_online')
    list_filter = ('is_admin', 'is_staff_member', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_admin', 'is_staff_member', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'last_activity')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_admin', 'is_staff_member'),
        }),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)

# Result Admin
@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'school_class', 'term', 'academic_year', 'total_score', 'grade', 'is_approved', 'teacher')
    list_filter = ('term', 'academic_year', 'is_approved', 'subject', 'school_class', 'teacher')
    search_fields = ('student__first_name', 'student__last_name', 'subject__name', 'school_class__name')
    readonly_fields = ('total_score', 'grade', 'remark', 'date_created', 'date_approved')
    fieldsets = (
        (None, {'fields': ('student', 'subject', 'school_class', 'term', 'academic_year')}),
        ('Scores', {'fields': ('exam_score', 'test_score', 'assignment_score', 'total_score', 'grade', 'remark')}),
        ('Approval', {'fields': ('teacher', 'is_approved', 'approved_by', 'date_approved')}),
        ('Timestamps', {'fields': ('date_created',)}),
    )
    actions = ['approve_results']

    def approve_results(self, request, queryset):
        queryset.update(is_approved=True, approved_by=request.user, date_approved=timezone.now())
    approve_results.short_description = "Approve selected results"

# Other Model Admins
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
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'position', 'campus')
    list_filter = ('position', 'campus')
    search_fields = ('first_name', 'last_name', 'email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_date', 'is_published')
    list_filter = ('is_published', 'published_date')
    search_fields = ('title', 'content')
    readonly_fields = ('published_date', 'updated_date')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author_name', 'content')
    actions = ['approve_comments']

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "Approve selected comments"

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'published_date', 'is_published')
    list_filter = ('media_type', 'is_published')
    search_fields = ('title',)
    readonly_fields = ('published_date',)

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at')
    search_fields = ('user__username', 'code')
    readonly_fields = ('created_at', 'activation_code_expires')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'created_at')
    search_fields = ('participants__username',)
    readonly_fields = ('created_at', 'updated_at')

    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('timestamp', 'read_at')

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'video_id', 'published_at', 'is_featured')
    list_filter = ('is_featured', 'published_at')
    search_fields = ('title', 'video_id')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'teacher', 'academic_year', 'student_count')
    list_filter = ('level', 'academic_year')
    search_fields = ('name', 'teacher__first_name')
    filter_horizontal = ('students',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CourseCatalog)
class CourseCatalogAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    list_filter = ('is_active', 'academic_year')
    search_fields = ('title',)
    readonly_fields = ('created_at',)

@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    list_filter = ('is_active', 'academic_year')
    search_fields = ('title',)
    readonly_fields = ('created_at',)

@admin.register(AcademicAnnouncement)
class AcademicAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_published')
    list_filter = ('is_published', 'date')
    search_fields = ('title',)
    readonly_fields = ('created_at',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'level')
    list_filter = ('level',)
    search_fields = ('name', 'code')

# Register Custom User
admin.site.register(User, CustomUserAdmin)