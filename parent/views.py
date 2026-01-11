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
from django.http import HttpResponse
from student.services.pdf_export_service import generate_driving_hours_pdf
from parent.models.parent_invitation import ParentInvitation
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

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
def edit_parent_profile(request):
    """
    Edit parent profile information including photo
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can edit their profile.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Update user information
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')

        # Update profile information
        parent_profile.phone = request.POST.get('phone', '')
        parent_profile.address1 = request.POST.get('address1', '')
        parent_profile.address2 = request.POST.get('address2', '')
        parent_profile.city = request.POST.get('city', '')
        parent_profile.state = request.POST.get('state', '')
        parent_profile.zipcode = request.POST.get('zipcode', '')

        # Handle photo upload
        if 'photo' in request.FILES:
            from core.services.photo_utils import validate_photo, process_profile_photo

            photo = request.FILES['photo']
            is_valid, error_message = validate_photo(photo)

            if not is_valid:
                messages.error(request, error_message)
                return render(request, 'parent/edit_profile.html', {
                    'parent_profile': parent_profile
                })

            # Get rotation value
            rotation = int(request.POST.get('rotation', 0))

            # Process the photo
            try:
                processed_photo = process_profile_photo(photo, rotation)

                # Delete old photo if exists
                if parent_profile.photo:
                    parent_profile.photo.delete(save=False)

                parent_profile.photo = processed_photo
            except Exception as e:
                messages.error(request, f'Error processing image: {str(e)}')
                return render(request, 'parent/edit_profile.html', {
                    'parent_profile': parent_profile
                })

        # Handle photo removal
        if request.POST.get('remove_photo') == 'true':
            if parent_profile.photo:
                parent_profile.photo.delete(save=False)
                parent_profile.photo = None

        # Validation
        if not request.user.first_name or not request.user.last_name:
            messages.error(request, 'First name and last name are required.')
            return render(request, 'parent/edit_profile.html', {
                'parent_profile': parent_profile
            })

        if not request.user.email:
            messages.error(request, 'Email is required.')
            return render(request, 'parent/edit_profile.html', {
                'parent_profile': parent_profile
            })

        try:
            request.user.save()
            parent_profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('parent_dashboard')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    context = {
        'parent_profile': parent_profile,
    }

    return render(request, 'parent/edit_profile.html', context)

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
    Edit student information including photo
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

        # Handle photo upload
        if 'photo' in request.FILES:
            from core.services.photo_utils import validate_photo, process_profile_photo

            photo = request.FILES['photo']
            is_valid, error_message = validate_photo(photo)

            if not is_valid:
                messages.error(request, error_message)
                return render(request, 'parent/edit_student.html', {'student': student})

            # Get rotation value
            rotation = int(request.POST.get('rotation', 0))

            # Process the photo
            try:
                processed_photo = process_profile_photo(photo, rotation)

                # Delete old photo if exists
                if student.photo:
                    student.photo.delete(save=False)

                student.photo = processed_photo
            except Exception as e:
                messages.error(request, f'Error processing image: {str(e)}')
                return render(request, 'parent/edit_student.html', {'student': student})

        # Handle photo removal
        if request.POST.get('remove_photo') == 'true':
            if student.photo:
                student.photo.delete(save=False)
                student.photo = None

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


@login_required
def export_student_hours_pdf(request, student_id):
    """
    Export student driving hours as PDF for DMV submission
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can export student reports.")

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
        raise PermissionDenied("You don't have permission to export this student's report.")

    # Get only approved trips (these are the official hours)
    trips = Trip.objects.filter(
        student=student,
        is_approved=True,
        is_active=False
    ).order_by('start_time')

    if not trips.exists():
        messages.warning(request,
                         f"No approved driving sessions found for {student.first_name}. Approve some trips first.")
        return redirect('view_student', student_id=student.id)

    # Generate PDF
    try:
        pdf = generate_driving_hours_pdf(student, trips, parent_profile)

        # Create the response
        response = HttpResponse(content_type='application/pdf')
        response[
            'Content-Disposition'] = f'attachment; filename="driving_hours_{student.first_name}_{student.last_name}.pdf"'
        response.write(pdf)

        return response

    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('view_student', student_id=student.id)


# ============================================
# PARENT INVITATION VIEWS
# ============================================

@login_required
def invite_parent(request, student_id):
    """
    Send an invitation to another parent/guardian to access a student
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can invite other parents.")

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
        raise PermissionDenied("You don't have permission to invite parents for this student.")

    if request.method == 'POST':
        invited_email = request.POST.get('invited_email', '').strip().lower()
        invited_first_name = request.POST.get('invited_first_name', '').strip()
        invited_last_name = request.POST.get('invited_last_name', '').strip()
        message = request.POST.get('message', '').strip()

        # Validation
        if not invited_email:
            messages.error(request, 'Email address is required.')
            return render(request, 'parent/invite_parent.html', {'student': student})

        # Check if inviting self
        if invited_email == request.user.email:
            messages.error(request, 'You cannot invite yourself.')
            return render(request, 'parent/invite_parent.html', {'student': student})

        # Check if this email already has access to this student
        from core.models.custom_user import AccountUser
        existing_user = AccountUser.objects.filter(email=invited_email).first()
        if existing_user and existing_user.user_type == 'PARENT':
            try:
                existing_parent = ParentProfile.objects.get(user=existing_user)
                if ParentStudentRelationship.objects.filter(
                        parent=existing_parent,
                        student=student
                ).exists():
                    messages.error(request, f'{invited_email} already has access to this student.')
                    return render(request, 'parent/invite_parent.html', {'student': student})
            except ParentProfile.DoesNotExist:
                pass

        # Check for existing pending invitation
        existing_invitation = ParentInvitation.objects.filter(
            student=student,
            invited_email=invited_email,
            status='PENDING'
        ).first()

        if existing_invitation:
            if not existing_invitation.is_expired():
                messages.warning(request,
                                 f'An invitation to {invited_email} is already pending. '
                                 f'Expires on {existing_invitation.expires_at.strftime("%B %d, %Y")}.')
                return redirect('view_student', student_id=student.id)
            else:
                # Mark old invitation as expired
                existing_invitation.mark_expired()

        try:
            # Create invitation
            invitation = ParentInvitation.objects.create(
                inviter=parent_profile,
                student=student,
                invited_email=invited_email,
                invited_first_name=invited_first_name,
                invited_last_name=invited_last_name,
                message=message
            )

            # Send invitation email
            current_site = get_current_site(request)
            invitation_url = request.build_absolute_uri(
                reverse('accept_invitation', kwargs={'token': invitation.token})
            )

            subject = f"You've been invited to help track {student.first_name}'s driving hours"

            email_message = f"""Hello{' ' + invited_first_name if invited_first_name else ''},

{request.user.get_full_name()} has invited you to help track driving hours for {student.first_name} {student.last_name} on DMV+.

"""
            if message:
                email_message += f"Personal message from {request.user.get_full_name()}:\n\"{message}\"\n\n"

            email_message += f"""To accept this invitation and create your account (or link to your existing account), click the link below:

{invitation_url}

This invitation will expire on {invitation.expires_at.strftime('%B %d, %Y at %I:%M %p')}.

Once you accept, you'll be able to:
- Log driving sessions for {student.first_name}
- Approve driving hours
- View {student.first_name}'s progress
- Export reports for the DMV

---
DMV+ - Drive, Manage, Verify
This is an automated message. Please do not reply to this email.
"""

            send_mail(
                subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [invited_email],
                fail_silently=False,
            )

            messages.success(request,
                             f'Invitation sent to {invited_email}! They will receive an email with instructions.')
            return redirect('view_student', student_id=student.id)

        except Exception as e:
            messages.error(request, f'Error sending invitation: {str(e)}')
            return render(request, 'parent/invite_parent.html', {'student': student})

    context = {
        'student': student,
    }

    return render(request, 'parent/invite_parent.html', context)


@login_required
def view_invitations(request, student_id):
    """
    View all invitations for a student
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can view invitations.")

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
        raise PermissionDenied("You don't have permission to view invitations for this student.")

    # Get all invitations for this student
    invitations = ParentInvitation.objects.filter(
        student=student
    ).select_related('inviter__user', 'accepted_by__user')

    # Mark expired invitations
    for invitation in invitations:
        if invitation.status == 'PENDING':
            invitation.mark_expired()

    context = {
        'student': student,
        'invitations': invitations,
    }

    return render(request, 'parent/view_invitations.html', context)


@login_required
def cancel_invitation(request, invitation_id):
    """
    Cancel a pending invitation
    """
    if request.user.user_type != 'PARENT':
        raise PermissionDenied("Only parents can cancel invitations.")

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
    except ParentProfile.DoesNotExist:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard')

    invitation = get_object_or_404(ParentInvitation, invitation_id=invitation_id)

    # Verify the current user is the inviter
    if invitation.inviter != parent_profile:
        raise PermissionDenied("You don't have permission to cancel this invitation.")

    if request.method == 'POST':
        if invitation.cancel():
            messages.success(request, 'Invitation cancelled successfully.')
        else:
            messages.warning(request, 'Invitation could not be cancelled (may already be accepted or expired).')

        return redirect('view_invitations', student_id=invitation.student.id)

    context = {
        'invitation': invitation,
    }

    return render(request, 'parent/cancel_invitation.html', context)


def accept_invitation(request, token):
    """
    Accept an invitation (creates account if needed or links existing account)
    """
    invitation = get_object_or_404(ParentInvitation, token=token)

    # Check if invitation is valid
    if invitation.status != 'PENDING':
        messages.error(request, f'This invitation is {invitation.status.lower()} and cannot be accepted.')
        return redirect('login')

    if invitation.is_expired():
        invitation.mark_expired()
        messages.error(request, 'This invitation has expired. Please ask for a new invitation.')
        return redirect('login')

    # If user is already logged in as a parent
    if request.user.is_authenticated and request.user.user_type == 'PARENT':
        try:
            parent_profile = ParentProfile.objects.get(user=request.user)

            # Check if they already have access
            if ParentStudentRelationship.objects.filter(
                    parent=parent_profile,
                    student=invitation.student
            ).exists():
                messages.info(request, 'You already have access to this student.')
                return redirect('view_student', student_id=invitation.student.id)

            # Accept invitation and create relationship
            invitation.accept(parent_profile)
            ParentStudentRelationship.objects.create(
                parent=parent_profile,
                student=invitation.student
            )

            messages.success(request,
                             f'Invitation accepted! You now have access to {invitation.student.first_name}\'s profile.')
            return redirect('view_student', student_id=invitation.student.id)

        except ParentProfile.DoesNotExist:
            messages.error(request, "Parent profile not found.")
            return redirect('dashboard')

    # If not logged in, show registration/login page
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'login':
            # Handle login
            email = request.POST.get('email')
            password = request.POST.get('password')

            if not email or not password:
                messages.error(request, 'Please provide both email and password.')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

            user = authenticate(request, username=email, password=password)

            if user is not None:
                if user.user_type != 'PARENT':
                    messages.error(request, 'Only parent accounts can accept parent invitations.')
                    return render(request, 'parent/accept_invitation.html', {
                        'invitation': invitation,
                    })

                login(request, user)

                try:
                    parent_profile = ParentProfile.objects.get(user=user)

                    # Check if they already have access
                    if ParentStudentRelationship.objects.filter(
                            parent=parent_profile,
                            student=invitation.student
                    ).exists():
                        messages.info(request, 'You already have access to this student.')
                        return redirect('view_student', student_id=invitation.student.id)

                    # Accept invitation and create relationship
                    invitation.accept(parent_profile)
                    ParentStudentRelationship.objects.create(
                        parent=parent_profile,
                        student=invitation.student
                    )

                    messages.success(request,
                                     f'Welcome back! You now have access to {invitation.student.first_name}\'s profile.')
                    return redirect('view_student', student_id=invitation.student.id)

                except ParentProfile.DoesNotExist:
                    messages.error(request, "Parent profile not found.")
                    return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

        elif action == 'register':
            # Handle registration
            email = request.POST.get('email')
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')

            # Validation
            if not all([email, password, password_confirm, first_name, last_name]):
                messages.error(request, 'All fields are required.')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

            from core.models.custom_user import AccountUser
            if AccountUser.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered. Please login instead.')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

            # Create user
            try:
                user = AccountUser.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type='PARENT'
                )

                # Log the user in
                login(request, user)

                # Get the auto-created parent profile
                parent_profile = ParentProfile.objects.get(user=user)

                # Accept invitation and create relationship
                invitation.accept(parent_profile)
                ParentStudentRelationship.objects.create(
                    parent=parent_profile,
                    student=invitation.student
                )

                messages.success(request,
                                 f'Account created successfully! You now have access to {invitation.student.first_name}\'s profile.')
                return redirect('view_student', student_id=invitation.student.id)

            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
                return render(request, 'parent/accept_invitation.html', {
                    'invitation': invitation,
                })

    context = {
        'invitation': invitation,
    }

    return render(request, 'parent/accept_invitation.html', context)

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
