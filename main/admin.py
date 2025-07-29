from django.contrib import admin
from .models import (
    User, Campus, Level, Parent, Student, StaffMember, News, Comment, Gallery,
    EmailVerification, Conversation, Message, YouTubeVideo, SchoolClass,
    CourseCatalog, AcademicCalendar, AcademicAnnouncement, Subject, Result
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_admin', 'is_staff_member', 'is_online', 'last_activity')
    list_filter = ('is_admin', 'is_staff_member', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-last_activity',)
    fieldsets = (
        (None, {'fields': ('username', 'email', 'first_name', 'last_name', 'password')}),
        ('Permissions', {'fields': ('is_admin', 'is_staff_member', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Activity', {'fields': ('last_activity', 'last_login')}),
    )
    readonly_fields = ('last_activity', 'last_login')

@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location')
    list_filter = ('location',)
    fields = ('name', 'location', 'description', 'image')

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    fields = ('name', 'description')

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('created_at',)
    raw_id_fields = ('user',)
    fields = ('user', 'name', 'phone', 'email', 'address', 'profile_picture', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'admission_number', 'campus', 'level', 'parent', 'admission_date')
    search_fields = ('first_name', 'last_name', 'admission_number')
    list_filter = ('campus', 'level', 'gender', 'admission_date')
    raw_id_fields = ('user', 'campus', 'level', 'parent')
    fields = (
        'user', 'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth',
        'admission_number', 'campus', 'level', 'admission_date', 'parent',
        'profile_picture', 'created_at', 'updated_at'
    )
    readonly_fields = ('created_at', 'updated_at')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'campus', 'email', 'joined_date')
    search_fields = ('first_name', 'last_name', 'email', 'office_number')
    list_filter = ('position', 'campus', 'joined_date')
    raw_id_fields = ('user', 'campus')
    fields = (
        'user', 'first_name', 'middle_name', 'last_name', 'position', 'office_number',
        'office_location', 'specialization', 'campus', 'phone', 'email', 'joined_date',
        'image', 'created_at', 'updated_at'
    )
    readonly_fields = ('created_at', 'updated_at')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_date', 'is_published')
    search_fields = ('title', 'content')
    list_filter = ('is_published', 'published_date')
    raw_id_fields = ('author',)
    fields = ('title', 'content', 'image', 'author', 'is_published', 'published_date', 'updated_date')
    readonly_fields = ('published_date', 'updated_date')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'author_email', 'created_at', 'is_approved')
    search_fields = ('author_name', 'author_email', 'content')
    list_filter = ('is_approved', 'created_at')
    fields = ('content', 'author_name', 'author_email', 'is_approved', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'author', 'published_date', 'is_published')
    search_fields = ('title', 'description')
    list_filter = ('media_type', 'is_published', 'published_date')
    raw_id_fields = ('author',)
    fields = ('title', 'description', 'media_type', 'image', 'video', 'author', 'is_published', 'published_date')
    readonly_fields = ('published_date',)

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at')
    search_fields = ('user__username', 'user__email', 'code')
    raw_id_fields = ('user',)
    fields = ('user', 'code', 'created_at', 'activation_code_expires')
    readonly_fields = ('created_at', 'activation_code_expires')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant_names', 'created_at', 'updated_at')
    search_fields = ('participants__username',)
    list_filter = ('created_at', 'updated_at')
    raw_id_fields = ('participants',)
    fields = ('participants', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    def participant_names(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    participant_names.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'timestamp', 'is_read')
    search_fields = ('content', 'sender__username')
    list_filter = ('is_read', 'timestamp')
    raw_id_fields = ('conversation', 'sender')
    fields = ('conversation', 'sender', 'content', 'file', 'is_read', 'read_at', 'timestamp')
    readonly_fields = ('timestamp', 'read_at')

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'video_id', 'published_at', 'is_featured')
    search_fields = ('title', 'video_id')
    list_filter = ('is_featured', 'published_at')
    fields = ('title', 'description', 'video_id', 'published_at', 'thumbnail_url', 'duration', 'is_featured', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'teacher', 'academic_year', 'student_count')
    search_fields = ('name', 'academic_year')
    list_filter = ('level', 'academic_year')
    raw_id_fields = ('level', 'teacher', 'students')
    fields = ('name', 'level', 'teacher', 'students', 'academic_year', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CourseCatalog)
class CourseCatalogAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    search_fields = ('title', 'academic_year')
    list_filter = ('is_active', 'academic_year')
    fields = ('title', 'file', 'academic_year', 'is_active', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(AcademicCalendar)
class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    search_fields = ('title', 'academic_year')
    list_filter = ('is_active', 'academic_year')
    fields = ('title', 'file', 'academic_year', 'is_active', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(AcademicAnnouncement)
class AcademicAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_published')
    search_fields = ('title', 'content')
    list_filter = ('is_published', 'date')
    fields = ('title', 'content', 'date', 'is_published', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'level')
    search_fields = ('name', 'code')
    list_filter = ('level',)
    raw_id_fields = ('level',)
    fields = ('name', 'code', 'description', 'level')

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term', 'academic_year', 'total_score', 'grade', 'is_approved')
    search_fields = ('student__first_name', 'student__last_name', 'subject__name', 'academic_year')
    list_filter = ('term', 'academic_year', 'is_approved', 'grade')
    raw_id_fields = ('student', 'subject', 'school_class', 'teacher', 'approved_by')
    fields = (
        'student', 'subject', 'school_class', 'term', 'academic_year',
        'exam_score', 'test_score', 'assignment_score', 'total_score',
        'grade', 'remark', 'teacher', 'is_approved', 'approved_by',
        'date_approved', 'date_created'
    )
    readonly_fields = ('total_score', 'grade', 'remark', 'date_created', 'date_approved')