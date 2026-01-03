import uuid
from django.db import models


class Trip(models.Model):
    trip_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey('parent.ParentProfile', on_delete=models.CASCADE)
    student = models.ForeignKey('student.StudentProfile', on_delete=models.CASCADE)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)

    is_night = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    duration = models.IntegerField(default=0)

    gps_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.trip_id} Duration: {self.duration}"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            from student.services.driving_session_service import determine_night
            is_night = determine_night(self.start_time, self.end_time)
            self.is_night = is_night
            self.duration = int((self.end_time - self.start_time).total_seconds() / 60)
            print(self.duration)
        super().save(*args, **kwargs)