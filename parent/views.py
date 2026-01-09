from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import datetime
from parent.models.parent_profile import ParentProfile
from parent.models.parent_student_relationship import ParentStudentRelationship
from student.models.student_profile import StudentProfile
from student.models.driving_sessions import Trip


@login_required
def parent_dashboard(request):
    """
    Parent dashboard showing their students and recent activity
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can access this page.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found. Please contact support.")
        return redirect('dashboard')

    # Get all students related to this parent
    relationships = ParentStudentRelationship.objects.filter(
        parent=parent_profile
    ).select_related('student')

    students = [rel.student for rel in relationships]

    # Get recent trips for all students
    recent_trips = Trip.objects.filter(
        parent=parent_profile,
        student__in=students
    ).order_by('-start_time')[:10]

    context = {
        'parent_profile': parent_profile,
        'students': students,
        'student_count': len(students),
        'recent_trips': recent_trips,
    }

    return render(request, 'parent/dashboard.html', context)


@login_required
def add_student(request):
    """
    Add a new student profile
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can add students.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        permit_number = request.POST.get('permit_number', '')
        drivers_ed_completed = request.POST.get('drivers_ed_completed') == 'on'

        # Validation
        if not first_name or not last_name:
            messages.error(request, 'First name and last name are required.')
            return render(request, 'parent/add_student.html')

        try:
            # Create student profile
            student = StudentProfile.objects.create(
                first_name=first_name,
                last_name=last_name,
                permit_number=permit_number,
                drivers_ed_completed=drivers_ed_completed,
            )

            # Create relationship
            ParentStudentRelationship.objects.create(
                parent=parent_profile,
                student=student
            )

            messages.success(request, f'Student {first_name} {last_name} added successfully!')
            return redirect('parent_dashboard')

        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
            return render(request, 'parent/add_student.html')

    return render(request, 'parent/add_student.html')


@login_required
def view_student(request, student_id):
    """
    View detailed information about a specific student
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can view student details.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    # Get student and verify relationship
    student = get_object_or_404(StudentProfile, id=student_id)

    relationship = ParentStudentRelationship.objects.filter(
        parent=parent_profile,
        student=student
    ).first()

    if not relationship:
        raise PermissionDenied("You don't have permission to view this student.")

    # Get all trips for this student
    trips = Trip.objects.filter(student=student).order_by('-start_time')

    # Check for active trip (NEW)
    active_trip = trips.filter(is_active=True).first()
    has_active_trip = active_trip is not None
    active_trip_id = active_trip.trip_id if active_trip else None

    # Calculate total hours (only from approved, completed trips) - UPDATED
    approved_completed_trips = trips.filter(is_approved=True, is_active=False)
    total_minutes = sum(trip.duration for trip in approved_completed_trips if trip.duration)
    total_hours = total_minutes / 60
    night_trips = approved_completed_trips.filter(is_night=True)
    night_minutes = sum(trip.duration for trip in night_trips if trip.duration)
    night_hours = night_minutes / 60

    context = {
        'student': student,
        'trips': trips,
        'total_hours': round(total_hours, 2),
        'night_hours': round(night_hours, 2),
        'day_hours': round(total_hours - night_hours, 2),
        'trip_count': trips.count(),
        'has_active_trip': has_active_trip,  # NEW
        'active_trip_id': active_trip_id,    # NEW
    }

    return render(request, 'parent/view_student.html', context)


@login_required
def edit_student(request, student_id):
    """
    Edit student information
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can edit student information.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    student = get_object_or_404(StudentProfile, id=student_id)

    # Verify relationship
    relationship = ParentStudentRelationship.objects.filter(
        parent=parent_profile,
        student=student
    ).first()

    if not relationship:
        raise PermissionDenied("You don't have permission to edit this student.")

    if request.method == 'POST':
        student.first_name = request.POST.get('first_name')
        student.last_name = request.POST.get('last_name')
        student.permit_number = request.POST.get('permit_number', '')
        student.drivers_ed_completed = request.POST.get('drivers_ed_completed') == 'on'

        if not student.first_name or not student.last_name:
            messages.error(request, 'First name and last name are required.')
            return render(request, 'parent/edit_student.html', {'student': student})

        try:
            student.save()
            messages.success(request, f'Student {student.first_name} {student.last_name} updated successfully!')
            return redirect('view_student', student_id=student.id)
        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')

    context = {
        'student': student,
    }

    return render(request, 'parent/edit_student.html', context)


@login_required
def delete_student(request, student_id):
    """
    Delete a student (removes relationship, not the student profile itself)
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can remove students.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    student = get_object_or_404(StudentProfile, id=student_id)

    # Find and delete the relationship
    relationship = ParentStudentRelationship.objects.filter(
        parent=parent_profile,
        student=student
    ).first()

    if not relationship:
        raise PermissionDenied("You don't have permission to remove this student.")

    if request.method == 'POST':
        student_name = f"{student.first_name} {student.last_name}"
        relationship.delete()
        messages.success(request, f'Student {student_name} removed from your account.')
        return redirect('parent_dashboard')

    context = {
        'student': student,
    }

    return render(request, 'parent/delete_student.html', context)


# ============================================
# TRIP LOGGING VIEWS
# ============================================

@login_required
def log_trip(request, student_id):
    """
    Log a new driving trip for a student
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can log trips.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    student = get_object_or_404(StudentProfile, id=student_id)

    # Verify relationship
    relationship = ParentStudentRelationship.objects.filter(
        parent=parent_profile,
        student=student
    ).first()

    if not relationship:
        raise PermissionDenied("You don't have permission to log trips for this student.")

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        start_time = request.POST.get('start_time')
        end_date = request.POST.get('end_date')
        end_time = request.POST.get('end_time')

        # Validation
        if not all([start_date, start_time, end_date, end_time]):
            messages.error(request, 'All date and time fields are required.')
            return render(request, 'parent/log_trip.html', {'student': student})

        try:
            # Combine date and time
            start_datetime_str = f"{start_date} {start_time}"
            end_datetime_str = f"{end_date} {end_time}"

            start_datetime = timezone.make_aware(
                datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
            )
            end_datetime = timezone.make_aware(
                datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')
            )

            # Validate times
            if end_datetime <= start_datetime:
                messages.error(request, 'End time must be after start time.')
                return render(request, 'parent/log_trip.html', {'student': student})

            if start_datetime > timezone.now():
                messages.error(request, 'Start time cannot be in the future.')
                return render(request, 'parent/log_trip.html', {'student': student})

            # Create trip
            trip = Trip.objects.create(
                parent=parent_profile,
                student=student,
                start_time=start_datetime,
                end_time=end_datetime
            )

            messages.success(request, f'Driving session logged successfully! Duration: {trip.duration} minutes')
            return redirect('view_student', student_id=student.id)

        except ValueError as e:
            messages.error(request, f'Invalid date/time format: {str(e)}')
            return render(request, 'parent/log_trip.html', {'student': student})
        except Exception as e:
            messages.error(request, f'Error logging trip: {str(e)}')
            return render(request, 'parent/log_trip.html', {'student': student})

    context = {
        'student': student,
        'today': timezone.now().date(),
        'now': timezone.now().strftime('%H:%M'),
    }

    return render(request, 'parent/log_trip.html', context)


@login_required
def view_trip(request, trip_id):
    """
    View details of a specific trip
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can view trip details.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    trip = get_object_or_404(Trip, trip_id=trip_id)

    # Verify parent owns this trip
    if trip.parent != parent_profile:
        raise PermissionDenied("You don't have permission to view this trip.")

    context = {
        'trip': trip,
        'student': trip.student,
    }

    return render(request, 'parent/view_trip.html', context)

@login_required
def approve_trip(request, trip_id):
    """
    Approve a trip - makes it read-only
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can approve trips.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    trip = get_object_or_404(Trip, trip_id=trip_id)

    # Verify parent owns this trip
    if trip.parent != parent_profile:
        raise PermissionDenied("You don't have permission to approve this trip.")

    if trip.is_approved:
        messages.info(request, 'This trip is already approved.')
        return redirect('view_trip', trip_id=trip.trip_id)

    if request.method == 'POST':
        trip.is_approved = True
        trip.save()
        messages.success(request, 'Trip approved successfully! This trip is now read-only.')
        return redirect('view_trip', trip_id=trip.trip_id)

    context = {
        'trip': trip,
        'student': trip.student,
    }

    return render(request, 'parent/approve_trip.html', context)

# Replace the existing edit_trip function in parent/views.py

@login_required
@login_required
def edit_trip(request, trip_id):
    """
    Edit an existing trip (not allowed for active or approved trips)
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can edit trips.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    trip = get_object_or_404(Trip, trip_id=trip_id)

    # Verify parent owns this trip
    if trip.parent != parent_profile:
        raise PermissionDenied("You don't have permission to edit this trip.")

    # Check if trip is active (NEW)
    if trip.is_active:
        messages.error(request, "Cannot edit an active trip. Please stop the trip first.")
        return redirect('active_trip', trip_id=trip.trip_id)

    # Check if trip is approved (NEW - add this if not already there)
    if trip.is_approved:
        messages.error(request, "Cannot edit an approved trip.")
        return redirect('view_trip', trip_id=trip.trip_id)

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        start_time = request.POST.get('start_time')
        end_date = request.POST.get('end_date')
        end_time = request.POST.get('end_time')

        if not all([start_date, start_time, end_date, end_time]):
            messages.error(request, 'All date and time fields are required.')
            return render(request, 'parent/edit_trip.html', {'trip': trip, 'student': trip.student})

        try:
            # Combine date and time
            start_datetime_str = f"{start_date} {start_time}"
            end_datetime_str = f"{end_date} {end_time}"

            start_datetime = timezone.make_aware(
                datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
            )
            end_datetime = timezone.make_aware(
                datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M')
            )

            # Validate times
            if end_datetime <= start_datetime:
                messages.error(request, 'End time must be after start time.')
                return render(request, 'parent/edit_trip.html', {'trip': trip, 'student': trip.student})

            # Update trip
            trip.start_time = start_datetime
            trip.end_time = end_datetime
            trip.save()

            messages.success(request, 'Trip updated successfully!')
            return redirect('view_trip', trip_id=trip.trip_id)

        except ValueError as e:
            messages.error(request, f'Invalid date/time format: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating trip: {str(e)}')

    context = {
        'trip': trip,
        'student': trip.student,
    }

    return render(request, 'parent/edit_trip.html', context)


@login_required
def delete_trip(request, trip_id):
    """
    Delete a trip (including active trips if under minimum duration)
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can delete trips.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    trip = get_object_or_404(Trip, trip_id=trip_id)

    # Verify parent owns this trip
    if trip.parent != parent_profile:
        raise PermissionDenied("You don't have permission to delete this trip.")

    student_id = trip.student.id

    # NEW: Allow deletion of active trips (for cancellation)
    if trip.is_active:
        messages.warning(request, 'Active trip cancelled.')

    # Prevent deletion of approved trips
    if trip.is_approved:
        messages.error(request, "Cannot delete an approved trip.")
        return redirect('view_trip', trip_id=trip.trip_id)

    if request.method == 'POST':
        trip.delete()
        messages.success(request, 'Trip deleted successfully!')
        return redirect('view_student', student_id=student_id)

    context = {
        'trip': trip,
        'student': trip.student,
    }

    return render(request, 'parent/delete_trip.html', context)

# ============================================
# TIMER-BASED TRIP VIEWS (NEW)
# ============================================

@login_required
def start_trip(request, student_id):
    """
    Start a new trip with timer
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can start trips.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    student = get_object_or_404(StudentProfile, id=student_id)

    # Verify relationship
    relationship = ParentStudentRelationship.objects.filter(
        parent=parent_profile,
        student=student
    ).first()

    if not relationship:
        raise PermissionDenied("You don't have permission to log trips for this student.")

    # Check if there's already an active trip for this student
    active_trip = Trip.objects.filter(
        student=student,
        parent=parent_profile,
        is_active=True
    ).first()

    if active_trip:
        messages.info(request, 'There is already an active trip for this student.')
        return redirect('active_trip', trip_id=active_trip.trip_id)

    if request.method == 'POST':
        try:
            # Create new active trip
            trip = Trip.objects.create(
                parent=parent_profile,
                student=student,
                start_time=timezone.now(),
                is_active=True
            )

            messages.success(request, f'Trip started for {student.first_name}!')
            return redirect('active_trip', trip_id=trip.trip_id)

        except Exception as e:
            messages.error(request, f'Error starting trip: {str(e)}')
            return redirect('view_student', student_id=student.id)

    context = {
        'student': student,
        'today': timezone.now(),
        'now': timezone.now(),
    }

    return render(request, 'parent/start_trip.html', context)


@login_required
def active_trip(request, trip_id):
    """
    Display active trip with timer
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can view trip details.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    trip = get_object_or_404(Trip, trip_id=trip_id)

    # Verify parent owns this trip
    if trip.parent != parent_profile:
        raise PermissionDenied("You don't have permission to view this trip.")

    # Verify trip is active
    if not trip.is_active:
        messages.info(request, 'This trip has already ended.')
        return redirect('view_trip', trip_id=trip.trip_id)

    context = {
        'trip': trip,
        'student': trip.student,
    }

    return render(request, 'parent/active_trip.html', context)


@login_required
def stop_trip(request, trip_id):
    """
    Stop an active trip (must be at least 5 minutes) or cancel it
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can stop trips.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    trip = get_object_or_404(Trip, trip_id=trip_id)

    # Verify parent owns this trip
    if trip.parent != parent_profile:
        raise PermissionDenied("You don't have permission to stop this trip.")

    # Verify trip is active
    if not trip.is_active:
        messages.error(request, 'This trip is not active.')
        return redirect('view_trip', trip_id=trip.trip_id)

    if request.method == 'POST':
        # Check if this is a cancel request
        if request.POST.get('cancel_trip') == 'true':
            student_id = trip.student.id
            trip.delete()
            messages.warning(request, 'Trip cancelled. No time was recorded.')
            return redirect('view_student', student_id=student_id)

        # Otherwise, try to stop the trip normally
        try:
            # Calculate duration before stopping
            end_time = timezone.now()
            duration_seconds = (end_time - trip.start_time).total_seconds()
            duration_minutes = int(duration_seconds / 60)

            # Check minimum duration
            from django.conf import settings
            min_duration = getattr(settings, 'MINIMUM_TRIP_DURATION', 5)

            if duration_minutes < min_duration:
                messages.error(
                    request,
                    f'Trip must be at least {min_duration} minutes long. '
                    f'Current duration: {duration_minutes} minute(s). '
                    f'Please continue driving or cancel the trip.'
                )
                return redirect('stop_trip', trip_id=trip.trip_id)

            # Stop the trip
            trip.end_time = end_time
            trip.is_active = False
            trip.save()

            messages.success(request, f'Trip stopped! Duration: {trip.duration} minutes')
            return redirect('view_trip', trip_id=trip.trip_id)

        except Exception as e:
            messages.error(request, f'Error stopping trip: {str(e)}')
            return redirect('active_trip', trip_id=trip.trip_id)

    # For GET request, calculate current duration for display
    current_duration_seconds = (timezone.now() - trip.start_time).total_seconds()
    current_duration_minutes = int(current_duration_seconds / 60)

    from django.conf import settings
    min_duration = getattr(settings, 'MINIMUM_TRIP_DURATION', 5)

    context = {
        'trip': trip,
        'student': trip.student,
        'current_duration_minutes': current_duration_minutes,
        'minimum_duration': min_duration,
    }

    return render(request, 'parent/stop_trip.html', context)
