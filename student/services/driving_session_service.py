from django.conf import settings
from django.db import transaction
from django.core.exceptions import PermissionDenied
from parent.models.parent_student_relationship import ParentStudentRelationship
from student.models.driving_sessions import Trip



def is_night(self, start_time, end_time):
    start_t = start_time.time()
    end_t = end_time.time()

    if start_time.date() != end_time.date():
        return True

    if end_t is None:
        if start_t >= settings.NIGHT_START:
            return True
        elif start_t <= settings.NIGHT_START and end_t > settings.NIGHT_START:
            return True

    return False

def get_duration(self, start_time, end_time):
    start_t = start_time.time()
    end_t = end_time.time()
    return int(end_t - start_t)

@transaction.atomic
def create_trip(*, parent_profile, student_profile, start_time, end_time):
    relationship = ParentStudentRelationship.objects.filter(
        parent=parent_profile,
        student=student_profile
    ).first()

    if not relationship:
        raise PermissionDenied("Parent not authorized to log hours for this student.")

    session = Trip.objects.create(
        parent=parent_profile,
        student=student_profile,
        start_time=start_time,
        end_time=end_time
    )