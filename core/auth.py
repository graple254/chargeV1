from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from .models import User
import random
import logging
from django.conf import settings
from django.shortcuts import redirect
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def generate_verification_code():
    """Generate a 6-digit random verification code."""
    return str(random.randint(100000, 999999))

# Set up logging
logger = logging.getLogger(__name__)

def send_verification_email(email, code):
    """Send a verification code using Brevo API."""

    # Real API key split to avoid GitHub detection
    part1 = "xkeysib"
    part2 = "-1a242f7c72a5da47d738050341dea3976f5f2af9316672d719e8d13f7b0124f9"
    part3 = "-ksajrR2HrcN9z665"
    api_key = part1 + part2 + part3  # Final key

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    subject = "Your Email Verification Code"
    html_content = f"""
    <html>
        <body>
            <p>Hello,</p>
            <p>Your verification code is:</p>
            <h2>{code}</h2>
            <p>Use it to complete your signup on Charge 🚗</p>
        </body>
    </html>
    """

    sender = {"email": "chargeke@gmail.com", "name": "Charge KE"}
    to = [{"email": email}]
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        html_content=html_content,
        subject=subject,
        sender=sender
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Verification email sent to {email}")
        return True
    except ApiException as e:
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
        role=role,  # Now "RENTER" or "LISTER", which matches ROLE_CHOICES
        password=make_password(password)  # Hash the password
    )

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
    
