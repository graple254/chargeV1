from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from .models import User
import random
import smtplib
from django.core.mail import send_mail

def generate_verification_code():
    """Generate a 6-digit random verification code."""
    return str(random.randint(100000, 999999))

def send_verification_email(email, code):
    """Send a verification code to the user's email."""
    subject = "Your Email Verification Code"
    message = f"Use this code to verify your email: {code}"
    from_email = "noreply@yourapp.com"  # Replace with your email
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)

    return True


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
        "message": "User registered successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role,
        },
    }


def authenticate_user(request, username, password):
    """Handles user authentication and logs them in if valid."""
    user = authenticate(request, username=username, password=password)

    if user:
        login(request, user)
        return {"status": True, "user": user}
    else:
        return {"status": False, "error": "Invalid credentials"}

def logout_user(request):
    """Logs out the user."""
    logout(request)
    return {"status": True}
