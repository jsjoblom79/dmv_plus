from django.contrib import admin
from parent.models.parent_profile import ParentProfile
from parent.models.parent_student_relationship import ParentStudentRelationship
from parent.models.parent_invitation import ParentInvitation

@admin.register(ParentInvitation)
class ParentInvitationAdmin(admin.ModelAdmin):
    list_display = ['invited_email', 'student', 'inviter', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invited_email', 'invited_first_name', 'invited_last_name']
    readonly_fields = ['token', 'invitation_id', 'created_at']

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'state']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']

@admin.register(ParentStudentRelationship)
class ParentStudentRelationshipAdmin(admin.ModelAdmin):
    list_display = ['parent', 'student', 'created_at']
    list_filter = ['created_at']


