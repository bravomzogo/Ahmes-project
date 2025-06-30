from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
admin.site.site_header = "Ahmes Administration"
admin.site.site_title = "Ahmes Admin Portal"
admin.site.index_title = "Welcome to Ahmes Admin"
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
    Message
)

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_admin', 'is_staff_member')
    list_filter = ('is_staff', 'is_admin', 'is_staff_member')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin', 'is_staff_member', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Register your models here
admin.site.register(User, CustomUserAdmin)

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
    list_display = ('first_name', 'last_name', 'position', 'campus')
    list_filter = ('position', 'campus')
    search_fields = ('first_name', 'last_name', 'email')
    raw_id_fields = ('user',)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_date', 'is_published')
    list_filter = ('is_published', 'author')
    search_fields = ('title', 'content')
    date_hierarchy = 'published_date'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'created_at', 'is_approved')
    list_filter = ('is_approved',)
    search_fields = ('author_name', 'content')
    date_hierarchy = 'created_at'

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'author', 'published_date', 'is_published')
    list_filter = ('media_type', 'is_published')
    search_fields = ('title', 'description')

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'activation_code_expires')
    search_fields = ('user__username', 'user__email', 'code')
    raw_id_fields = ('user',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'created_at', 'updated_at')
    filter_horizontal = ('participants',)
    
    def get_participants(self, obj):
        return ", ".join([p.username for p in obj.participants.all()])
    get_participants.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'timestamp', 'is_read')
    list_filter = ('is_read', 'conversation')
    search_fields = ('content', 'sender__username')
    raw_id_fields = ('conversation', 'sender')
    date_hierarchy = 'timestamp'