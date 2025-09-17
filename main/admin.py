from datetime import timezone
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Campus, Level, Parent, Student, StaffMember, News, Comment, 
    Gallery, EmailVerification, Conversation, Message, YouTubeVideo,
    SchoolClass, CourseCatalog, AcademicCalendar, AcademicAnnouncement,
    Subject, Result
)
from django.utils.html import format_html
from django.urls import reverse


# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 
                    'is_parent', 'is_admin', 'is_staff_member', 'is_student',
                    'is_online', 'last_activity')
    list_filter = ('is_parent', 'is_admin', 'is_staff_member', 'is_student')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions')}),
        ('User Types', {'fields': ('is_parent', 'is_admin', 'is_staff_member', 'is_student')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'last_activity')}),
    )


# Parent Admin
class ParentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at', 'profile_picture_tag')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'profile_picture_tag')
    
    def profile_picture_tag(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.profile_picture.url))
        return "No Image"
    profile_picture_tag.short_description = 'Profile Picture'


# Student Admin
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'admission_number', 'gender', 'campus', 'level', 
                    'admission_date', 'parent_link', 'profile_picture_tag')
    list_filter = ('gender', 'campus', 'level')
    search_fields = ('first_name', 'last_name', 'admission_number', 'parent__name')
    readonly_fields = ('created_at', 'updated_at', 'profile_picture_tag')
    raw_id_fields = ('parent',)
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'
    
    def parent_link(self, obj):
        if obj.parent:
            url = reverse("admin:main_parent_change", args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.name)
        return "-"
    parent_link.short_description = 'Parent'
    
    def profile_picture_tag(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.profile_picture.url))
        return "No Image"
    profile_picture_tag.short_description = 'Profile Picture'


# Staff Member Admin
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'campus', 'specialization', 'joined_date', 'image_tag')
    list_filter = ('position', 'campus')
    search_fields = ('first_name', 'last_name', 'email', 'specialization')
    readonly_fields = ('created_at', 'updated_at', 'image_tag')
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.image.url))
        return "No Image"
    image_tag.short_description = 'Image'


# News Admin
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_date', 'is_published', 'image_tag')
    list_filter = ('is_published', 'published_date')
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('published_date', 'updated_date', 'image_tag')
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.image.url))
        return "No Image"
    image_tag.short_description = 'Image'


# Gallery Admin
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'author', 'published_date', 'is_published', 'media_preview')
    list_filter = ('media_type', 'is_published')
    search_fields = ('title', 'description')
    readonly_fields = ('published_date', 'media_preview')
    
    def media_preview(self, obj):
        if obj.media_type == 'image' and obj.image:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.image.url))
        elif obj.media_type == 'video' and obj.video:
            return "Video"
        return "No Media"
    media_preview.short_description = 'Preview'


# Message Admin
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'timestamp', 'is_read', 'content_preview', 'file_type')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('timestamp', 'read_at', 'file_preview')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def file_type(self, obj):
        if obj.file:
            return obj.file.resource_type
        return "-"
    file_type.short_description = 'File Type'
    
    def file_preview(self, obj):
        if obj.file:
            if obj.file.resource_type == 'image':
                return format_html('<img src="{}" width="150" />'.format(obj.file.url))
            elif obj.file.resource_type == 'video':
                return format_html('<video width="150" controls><source src="{}"></video>'.format(obj.file.url))
            return format_html('<a href="{}">Download File</a>'.format(obj.file.url))
        return "No File"
    file_preview.short_description = 'File Preview'


# YouTube Video Admin
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'video_id', 'published_at', 'is_featured', 'thumbnail_preview')
    list_filter = ('is_featured',)
    search_fields = ('title', 'description', 'video_id')
    readonly_fields = ('created_at', 'updated_at', 'thumbnail_preview')
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return format_html('<img src="{}" width="100" />'.format(obj.thumbnail_url))
        return "No Thumbnail"
    thumbnail_preview.short_description = 'Thumbnail'


# School Class Admin
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'teacher', 'academic_year', 'student_count')
    list_filter = ('level', 'academic_year')
    search_fields = ('name', 'teacher__first_name', 'teacher__last_name')
    filter_horizontal = ('students',)
    
    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = 'Students'


# Subject Admin
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'level')
    list_filter = ('level',)
    search_fields = ('name', 'code')


# Result Admin
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term',  'total_score', 'grade', 'is_approved')
    list_filter = ('term', 'grade', 'is_approved')
    search_fields = ('student__first_name', 'student__last_name', 'subject__name')
    readonly_fields = ('total_score', 'grade', 'remark')
    raw_id_fields = ('student', 'teacher', 'approved_by')
    
    def save_model(self, request, obj, form, change):
        if obj.is_approved and not obj.approved_by:
            obj.approved_by = request.user
            obj.date_approved = timezone.now()
        super().save_model(request, obj, form, change)


# Simple Model Admins (for models that don't need special configuration)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location')

class LevelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'content_preview', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author_name', 'content')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'activation_code_expires')
    search_fields = ('user__username', 'code')

class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participants_list', 'created_at', 'updated_at')
    filter_horizontal = ('participants',)
    
    def participants_list(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    participants_list.short_description = 'Participants'

class CourseCatalogAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    list_filter = ('academic_year', 'is_active')
    search_fields = ('title', 'academic_year')

class AcademicCalendarAdmin(admin.ModelAdmin):
    list_display = ('title', 'academic_year', 'is_active')
    list_filter = ('academic_year', 'is_active')
    search_fields = ('title', 'academic_year')

class AcademicAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_published')
    list_filter = ('is_published', 'date')
    search_fields = ('title', 'content')


from django.contrib import admin
from .models import PushSubscription

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'subscription_summary')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'subscription')
    date_hierarchy = 'created_at'

    def subscription_summary(self, obj):
        """Display a summary of the subscription JSON data."""
        subscription = obj.subscription
        try:
            endpoint = subscription.get('endpoint', 'N/A')
            return endpoint[:50] + '...' if len(endpoint) > 50 else endpoint
        except (TypeError, AttributeError):
            return 'Invalid subscription data'
    
    subscription_summary.short_description = 'Subscription Endpoint'


# Register all models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Level, LevelAdmin)
admin.site.register(Parent, ParentAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(StaffMember, StaffMemberAdmin)
admin.site.register(News, NewsAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(EmailVerification, EmailVerificationAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(YouTubeVideo, YouTubeVideoAdmin)
admin.site.register(SchoolClass, SchoolClassAdmin)
admin.site.register(CourseCatalog, CourseCatalogAdmin)
admin.site.register(AcademicCalendar, AcademicCalendarAdmin)
admin.site.register(AcademicAnnouncement, AcademicAnnouncementAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Result, ResultAdmin)



from django.contrib import admin
from .models import FeeStructure, Payment

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('level', 'academic_year', 'amount', 'is_active', 'created_at')
    list_filter = ('level', 'academic_year', 'is_active')
    search_fields = ('level__name', 'academic_year', 'description')
    ordering = ('-created_at',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('control_number', 'student', 'fee_structure', 'amount_paid', 'payment_method', 'payment_date', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'payment_date', 'created_at')
    search_fields = ('control_number', 'student__first_name', 'student__last_name', 'transaction_reference', 'receipt_number')
    ordering = ('-payment_date',)




from django.contrib import admin
from .models import InventoryCategory, InventoryItem, InventoryTransaction

@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    list_filter = ('name',)
    search_fields = ('name', 'description')

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity', 'unit', 'unit_price', 'total_value', 'status', 'created_at')
    list_filter = ('category', 'status', 'created_at')
    search_fields = ('name', 'description', 'location', 'supplier')
    readonly_fields = ('total_value', 'status', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'category')
        }),
        ('Stock Information', {
            'fields': ('quantity', 'unit', 'unit_price', 'total_value', 'minimum_stock', 'status')
        }),
        ('Additional Information', {
            'fields': ('location', 'supplier', 'notes')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'last_updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.last_updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('item', 'transaction_type', 'quantity', 'unit_price', 'total_value', 'created_by', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('item__name', 'notes')
    readonly_fields = ('total_value', 'created_at')
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
