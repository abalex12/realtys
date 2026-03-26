from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import User, SavedListing
from .forms import RegisterForm, LoginForm, ProfileForm, CustomPasswordChangeForm
from .email_utils import send_verification_email, send_password_reset_email


# ── Registration & Email Verification ─────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = False
            user.is_active = True  # allow login but restrict posting until verified
            user.save()
            # Send verification email
            sent = send_verification_email(user, request)
            login(request, user)
            if sent:
                messages.success(request,
                    '🎉 Account created! Please check your email to verify your address. '
                    'Check the terminal/console in development mode.')
            else:
                messages.warning(request,
                    'Account created but we could not send the verification email. '
                    'You can resend it from your dashboard.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, token):
    try:
        token_uuid = uuid.UUID(str(token))
    except (ValueError, AttributeError):
        messages.error(request, 'Invalid verification link.')
        return redirect('home')

    user = get_object_or_404(User, email_verification_token=token_uuid)

    if user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('dashboard')

    # Check expiry: 24 hours
    if user.email_verification_sent_at:
        expiry = user.email_verification_sent_at + timedelta(hours=24)
        if timezone.now() > expiry:
            messages.error(request,
                'This verification link has expired. '
                '<a href="/accounts/resend-verification/">Click here to resend</a>.')
            return redirect('login')

    user.email_verified = True
    user.save(update_fields=['email_verified'])
    messages.success(request, '✅ Email verified! You can now post listings.')
    if not request.user.is_authenticated:
        login(request, user)
    return redirect('dashboard')


@login_required
def resend_verification(request):
    if request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('dashboard')
    if request.method == 'POST':
        sent = send_verification_email(request.user, request)
        if sent:
            messages.success(request, 'Verification email resent! Check your inbox (and console in dev mode).')
        else:
            messages.error(request, 'Could not send email. Please try again later.')
        return redirect('dashboard')
    return render(request, 'accounts/resend_verification.html')


# ── Login / Logout ─────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ── Password Reset ─────────────────────────────────────────────────────────────

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email=email)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                site_url = request.build_absolute_uri('/').rstrip('/')
                reset_url = f"{site_url}/accounts/password-reset/confirm/{uid}/{token}/"
                send_password_reset_email(user, reset_url)
            except User.DoesNotExist:
                pass  # Don't reveal whether email exists
        messages.success(request,
            'If an account with that email exists, a reset link has been sent. '
            'Check the terminal in development mode.')
        return redirect('login')
    return render(request, 'accounts/password_reset.html')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, User.DoesNotExist):
        user = None

    valid = user is not None and default_token_generator.check_token(user, token)
    if not valid:
        messages.error(request, 'This password reset link is invalid or has expired.')
        return redirect('password_reset_request')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Password changed successfully. You can now sign in.')
            return redirect('login')
    else:
        form = SetPasswordForm(user)
        for f in form.fields.values():
            f.widget.attrs['class'] = 'form-control'
    return render(request, 'accounts/password_reset_confirm.html', {'form': form})


# ── Profile ────────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '✅ Password changed successfully.')
            return redirect('profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


# ── Saved Listings ─────────────────────────────────────────────────────────────

@login_required
def saved_listings(request):
    saves = SavedListing.objects.filter(user=request.user).select_related('listing')
    return render(request, 'accounts/saved_listings.html', {'saves': saves})


@login_required
def toggle_save_listing(request, slug):
    from listings.models import Listing
    listing = get_object_or_404(Listing, slug=slug, status='approved')
    saved, created = SavedListing.objects.get_or_create(user=request.user, listing=listing)
    if not created:
        saved.delete()
        msg, icon = 'Removed from saved listings.', 'removed'
    else:
        msg, icon = 'Listing saved! View your saved listings from your dashboard.', 'saved'
    # AJAX response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({'status': icon, 'message': msg})
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'listing_detail'), slug=slug)
