from django.contrib import admin
from parent.models.parent_profile import ParentProfile
from parent.models.parent_student_relationship import ParentStudentRelationship

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'state']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']

@admin.register(ParentStudentRelationship)
class ParentStudentRelationshipAdmin(admin.ModelAdmin):
    list_display = ['parent', 'student', 'created_at']
    list_filter = ['created_at']


