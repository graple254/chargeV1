from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from .models import User
import random
import smtplib
from django.core.mail import send_mail
import logging
from django.conf import settings
from django.shortcuts import redirect

def generate_verification_code():
    """Generate a 6-digit random verification code."""
    return str(random.randint(100000, 999999))

# Set up logging
logger = logging.getLogger(__name__)

def send_verification_email(email, code):
    """Send a verification code to the user's email."""
    subject = "Your Email Verification Code"
    message = f"Use this code to verify your email: {code}"
    from_email = settings.DEFAULT_FROM_EMAIL  # Use the configured email
    recipient_list = [email]

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        logger.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        return False


def register_user(username, email, phone_number, role, password, confirm_password):
    """Handles user registration and returns a dictionary with the result."""

    if password != confirm_password:
        return {"status": False, "error": "Passwords do not match"}

    if User.objects.filter(username=username).exists():
        return {"status": False, "error": "Username already exists"}

    if User.objects.filter(email=email).exists():
        return {"status": False, "error": "Email already in use"}

    user = User.objects.create(
        username=username,
        email=email,
        phone_number=phone_number,
        role=role,
        password=make_password(password)  # Hash the password
    )

    # ✅ Return only serializable user data
    return {
        "status": True,
        "user": user.username
    }


def authenticate_user_func(request, username, password):
    """Handles user authentication and logs them in if valid."""
    if not username or not password:
        return {"status": False, "error": "Username and password are required"}

    user = authenticate(request, username=username, password=password)

    if user:
        login(request, user)
        return {"status": True, "user": user.username}
    else:
        return {"status": False, "error": "Invalid credentials"}
    
