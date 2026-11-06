from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import LoginForm


def get_role_redirect_url(user):
    """Returns the primary landing dashboard URL based on the user's role."""
    if user.is_doctor:
        return 'doctor-dashboard'
    elif user.is_patient:
        return 'patient-dashboard'
    elif user.is_admin_role:
        return 'admin-devices'
    return 'login'


def home_redirect_view(request):
    """
    Landing page redirector:
    - Unauthenticated users -> /login/
    - Authenticated users -> Redirected based on their role:
        Doctor  -> /doctor/dashboard/
        Patient -> /patient/dashboard/
        Admin   -> /admin-portal/devices/
    """
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect(get_role_redirect_url(request.user))


def login_view(request):
    """Role-aware user authentication view with support for pre-authenticated sessions."""
    if request.user.is_authenticated:
        return redirect(get_role_redirect_url(request.user))

    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(
                        request,
                        f"Welcome back, {user.get_full_name() or user.username}! Logged in as {user.get_role_display()}."
                    )
                    # Redirect to safe next URL if applicable
                    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    return redirect(get_role_redirect_url(user))
                else:
                    messages.error(request, "This account is inactive. Please contact your system administrator.")
            else:
                messages.error(request, "Invalid username or password. Please verify your credentials and try again.")
    else:
        form = LoginForm()

    demo_accounts = [
        {
            "role": "Admin",
            "username": "admin",
            "password": "AdminPassword123!",
            "name": "System Administrator",
            "badge_class": "bg-danger",
            "icon": "bi-shield-lock",
        },
        {
            "role": "Doctor (Cardiology)",
            "username": "dr.chen",
            "password": "DoctorPassword123!",
            "name": "Dr. Sarah Chen",
            "badge_class": "bg-primary",
            "icon": "bi-heart-pulse",
        },
        {
            "role": "Doctor (Endocrinology)",
            "username": "dr.patel",
            "password": "DoctorPassword123!",
            "name": "Dr. Marcus Patel",
            "badge_class": "bg-info text-dark",
            "icon": "bi-prescription2",
        },
        {
            "role": "Patient (Hypertension & CAD)",
            "username": "patient.johndoe",
            "password": "PatientPassword123!",
            "name": "John Doe",
            "badge_class": "bg-success",
            "icon": "bi-person-check",
        },
        {
            "role": "Patient (Type 2 Diabetes)",
            "username": "patient.mariagarcia",
            "password": "PatientPassword123!",
            "name": "Maria Garcia",
            "badge_class": "bg-success",
            "icon": "bi-person-check",
        },
    ]

    context = {
        'form': form,
        'next': next_url,
        'demo_accounts': demo_accounts,
    }
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    """Terminates session and returns user to login screen."""
    logout(request)
    messages.info(request, "You have been logged out successfully. Stay safe!")
    return redirect('login')
