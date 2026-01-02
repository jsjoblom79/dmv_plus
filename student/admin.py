from django.contrib import admin
from student.models.student_profile import StudentProfile
from student.models.driving_sessions import Trip
from student.models.driving_session_audit import TripSessionAudit

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'permit_number', 'drivers_ed_completed']
    search_fields = ['first_name', 'last_name', 'permit_number']

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['trip_id', 'student', 'parent', 'start_time', 'end_time', 'duration', 'is_night']
    list_filter = ['is_night', 'is_approved']
