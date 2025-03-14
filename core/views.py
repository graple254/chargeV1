from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from core.auth import * # Import from auth.py
import time

def authenticate_user(request):
    """Authenticate a user dynamically from any view."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return JsonResponse({"status": "success", "message": "Login successful!", "user": user.username})

        return JsonResponse({"status": "error", "message": "Invalid credentials"})

    return JsonResponse({"status": "error", "message": "Invalid request method"})



def send_verification_code(request):
    """Sends an email verification code to the user."""
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return JsonResponse({"status": False, "error": "Email is required"})

        code = generate_verification_code()
        request.session["email_verification_code"] = code
        request.session["email_verification_address"] = email
        request.session["email_verification_timestamp"] = time.time()  # Store timestamp

        send_verification_email(email, code)

        return JsonResponse({"status": True, "message": "Verification code sent!"})

    return JsonResponse({"status": False, "error": "Invalid request"})



def verify_email_code(request):
    """Checks if the entered code matches the stored code."""
    if request.method == "POST":
        code_entered = request.POST.get("code")
        stored_code = request.session.get("email_verification_code")
        timestamp = request.session.get("email_verification_timestamp")

        # Check if the code is expired (5-minute limit)
        if not stored_code:
            return JsonResponse({"status": False, "error": "No verification code found. Request a new one."})


        if stored_code == code_entered:
            request.session["verified_email"] = request.session["email_verification_address"]
            return JsonResponse({"status": True, "message": "Email verified successfully!"})

        return JsonResponse({"status": False, "error": "Invalid verification code"})

    return JsonResponse({"status": False, "error": "Invalid request"})


def user_signup(request):
    """Handles user signup after email verification."""
    if request.method == "POST":
        email = request.POST.get("email")

        # ✅ Check if email is verified
        if request.session.get("verified_email") != email:
            return JsonResponse({"status": False, "error": "Email not verified"})

        username = request.POST.get("username")
        phone_number = request.POST.get("phone_number")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Call registration function
        response = register_user(username, email, phone_number, role, password, confirm_password)
        
        if response["status"]:
            # ✅ Clear session after successful signup
            for key in [
                "verified_email",
                "email_verification_code",
                "email_verification_timestamp",
                "email_verification_address",
            ]:
                if key in request.session:
                    del request.session[key]

        return JsonResponse(response, safe=False)  # ✅ Ensure JSON response is serializable

    return JsonResponse({"status": False, "error": "Invalid request"})




def user_logout(request):
    """View to log out a user and return a response."""
    response = logout_user(request)  # Call function from auth.py
    return JsonResponse(response)