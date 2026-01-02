from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models.custom_user import AccountUser


def register_view(request):
    """
    Handle user registration
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        user_type = request.POST.get('user_type', 'PARENT')

        # Validation
        if not all([email, password, password_confirm, first_name, last_name]):
            messages.error(request, 'All fields are required.')
            return render(request, 'core/register.html')

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'core/register.html')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'core/register.html')

        if AccountUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'core/register.html')

        # Create user
        try:
            user = AccountUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type=user_type
            )

            # Log the user in
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'core/register.html')

    return render(request, 'core/register.html')


def login_view(request):
    """
    Handle user login
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'core/login.html')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')

            # Redirect to next page if specified, otherwise dashboard
            next_page = request.GET.get('next', 'dashboard')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'core/login.html')

    return render(request, 'core/login.html')


@login_required
def logout_view(request):
    """
    Handle user logout
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """
    Main dashboard - will route based on user type
    """
    user = request.user

    # Route to appropriate dashboard based on user type
    if user.user_type == 'PARENT':
        return redirect('parent_dashboard')
    elif user.user_type == 'STUDENT':
        return redirect('student_dashboard')
    else:
        # For undefined users, show a setup page
        return render(request, 'core/setup.html', {'user': user})