from django.conf import settings
from django.db import transaction
from django.core.exceptions import PermissionDenied
from parent.models.parent_student_relationship import ParentStudentRelationship
from student.models.driving_sessions import Trip



def determine_night(start_time, end_time):
    start_t = start_time.time()
    end_t = end_time.time()
    print(f"Start time: {start_t} | End time: {end_t}")
    # if end_t is None:
    #     return start_t >= settings.NIGHT_START
    print(f"Setting Start Time: {settings.NIGHT_START} | Setting End Time: {settings.NIGHT_END}")

    if start_t >= settings.NIGHT_START:
        return True

    if start_t < settings.NIGHT_START < end_t:
        return True

    return False

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