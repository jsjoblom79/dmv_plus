import uuid
from django.db import models
from student.services.driving_session_service import DrivingSessionService

class Trip(models.Model):
    trip_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey('parent.ParentProfile', on_delete=models.CASCADE)
    student = models.ForeignKey('student.StudentProfile', on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    is_night = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    duration = models.IntegerField(default=0)

    gps_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.trip_id} Duration: {self.duration}"

    def save(self, *args, **kwargs):
        if self.pk:
            is_night = DrivingSessionService.is_night(self.start_time, self.end_time)

        super().save(*args, **kwargs)