from django.db import models
from django.conf import settings

class StudentProfile(models.Model):
    # currently the student wont be able to login. only the parent can see the students.
    # at a later time the student will be able to create an AccountUser from an invite and claim.
    # their profile.
    # user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    permit_number = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    drivers_ed_date_completed = models.DateTimeField(blank=True, null=True)
    drivers_ed_completed = models.BooleanField(default=False)
    road_test_taken = models.DateTimeField(blank=True, null=True)
    road_test_passed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - Permit Number: {self.permit_number}"