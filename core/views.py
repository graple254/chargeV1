from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from core.auth import * # Import from auth.py
import time
from .decorators import role_required, block_listers
from .models import *
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
import json
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from django.core.files.storage import default_storage
from django.contrib import messages
from datetime import datetime
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
import re
import decimal
from django.utils.timezone import localtime, now
from datetime import timedelta
from decimal import Decimal





# Authenications views and Functionalities HERE 👇 ##############################################################################


def authenticate_user(request):
    """Authenticate a user and render the login template."""
    if request.method == "POST":
        # Handle AJAX login request
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({"status": True, "message": "Login successful!"})
        else:
            return JsonResponse({"status": False, "error": "Invalid username or password"})

# Render the login template for GET requests with ROLE_CHOICES
    next_url = request.GET.get("next", "/")
    return render(request, "renter/login.html", {
        "next": next_url,
        "role_choices": User.ROLE_CHOICES  # Pass the role choices to the template
    })

def send_verification_code(request):
    """Sends an email verification code to the user."""
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return JsonResponse({"status": False, "error": "Email is required"})

        # Rate limiting: Check if a code was sent recently (e.g., within 60 seconds)
        timestamp = request.session.get("email_verification_timestamp")
        if timestamp and (time.time() - timestamp) < 60:
            return JsonResponse({"status": False, "error": "Please wait 60 seconds before requesting a new code"})

        code = generate_verification_code()  # Ensure this function exists
        request.session["email_verification_code"] = code
        request.session["email_verification_address"] = email
        request.session["email_verification_timestamp"] = time.time()

        if send_verification_email(email, code):  # Ensure this function exists
            return JsonResponse({"status": True, "message": "Verification code sent to your email!"})
        else:
            return JsonResponse({"status": False, "error": "Failed to send verification code. Please try again."})

    return JsonResponse({"status": False, "error": "Invalid request"})

import time
import logging

# Set up logging
logger = logging.getLogger(__name__)

def verify_email_code(request):
    """Verifies the email code entered by the user against the stored code."""
    if request.method != "POST":
        logger.warning("Invalid request method: %s", request.method)
        return JsonResponse({"status": False, "error": "Invalid request method."}, status=405)

    code_entered = request.POST.get("code")
    stored_code = request.session.get("email_verification_code")
    timestamp = request.session.get("email_verification_timestamp")
    email = request.session.get("email_verification_address")

    # Validate input
    if not code_entered:
        logger.warning("No code provided in request.")
        return JsonResponse({"status": False, "error": "Please enter a verification code."}, status=400)

    # Check if verification data exists
    if not stored_code or not timestamp or not email:
        logger.error("Missing session data: code=%s, timestamp=%s, email=%s", stored_code, timestamp, email)
        return JsonResponse({"status": False, "error": "No verification code found. Please request a new one."}, status=400)

    # Check if the code is expired (10-minute limit)
    if time.time() - float(timestamp) > 600:  # 10 minutes = 600 seconds
        logger.info("Verification code expired for email: %s", email)
        # Clean up session
        session_keys = ["email_verification_code", "email_verification_address", "email_verification_timestamp"]
        for key in session_keys:
            request.session.pop(key, None)
        return JsonResponse({"status": False, "error": "Verification code has expired. Please request a new one."}, status=400)

    # Verify the code
    if stored_code == code_entered:
        logger.info("Successful email verification for: %s", email)
        request.session["verified_email"] = email
        # Clean up session
        session_keys = ["email_verification_code", "email_verification_address", "email_verification_timestamp"]
        for key in session_keys:
            request.session.pop(key, None)
        return JsonResponse({"status": True, "message": "Email verified successfully!"}, status=200)

    logger.warning("Invalid code entered for email: %s", email)
    return JsonResponse({"status": False, "error": "Invalid verification code."}, status=400)



def user_signup(request):
    """Handles user signup after email verification."""
    if request.method == "POST":
        email = request.POST.get("email")

        # Check if email is verified
        if request.session.get("verified_email") != email:
            return JsonResponse({"status": False, "error": "Email not verified"})

        username = request.POST.get("username")
        phone_number = request.POST.get("phone_number")
        role = request.POST.get("role")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Validate inputs
        if not all([username, email, phone_number, role, password, confirm_password]):
            return JsonResponse({"status": False, "error": "All fields are required"})

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return JsonResponse({"status": False, "error": "Invalid email format"})

        # Validate role against ROLE_CHOICES
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]  # ['RENTER', 'LISTER']
        if role not in valid_roles:
            return JsonResponse({"status": False, "error": "Invalid role"})

        # Register the user
        response = register_user(username, email, phone_number, role, password, confirm_password)
        
        if response["status"]:
            # Log the user in after signup
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                # Store the role in the session (mapped to lowercase for consistency)
                request.session["role"] = role.lower()  # "renter" or "lister"
            # Clear session after successful signup
            for key in [
                "verified_email",
                "email_verification_code",
                "email_verification_timestamp",
                "email_verification_address",
            ]:
                if key in request.session:
                    del request.session[key]
            return JsonResponse({"status": True, "message": "User registered successfully!"})

        return JsonResponse({"status": False, "error": response["error"]})

    return JsonResponse({"status": False, "error": "Invalid request"})    


def check_auth_status(request):
    """Check if the user is authenticated and has a profile."""
    data = {
        "is_authenticated": request.user.is_authenticated,
        "has_profile": False,
        "role": None,
    }
    if request.user.is_authenticated:
        try:
            # Check for RenterProfile
            RenterProfile.objects.get(user=request.user)
            data["has_profile"] = True
            data["role"] = "renter"
        except RenterProfile.DoesNotExist:
            try:
                # Check for ListerProfile
                ListerProfile.objects.get(user=request.user)
                data["has_profile"] = True
                data["role"] = "lister"
            except ListerProfile.DoesNotExist:
                # Get role from session or user model
                session_role = request.session.get("role")
                if session_role:
                    data["role"] = session_role  # Already lowercase ("renter" or "lister")
                else:
                    # Fallback to user model role
                    user_role = request.user.role  # "RENTER" or "LISTER"
                    data["role"] = user_role.lower() if user_role else "renter"  # Map to "renter" or "lister"
    return JsonResponse(data)
    
def logout_user(request):
    """Logs out the user and redirects to the start page."""
    logout(request)
    return redirect("start")

# END OF AUTHENTICATION VIEWS AND FUNCTIONALITIES #######################################################################


# Lister views and Functionalities HERE 👇 ##############################################################################
@login_required
@role_required("lister")
def lister_dashboard(request):
    """ Dashboard view for the car lister """
    user = request.user
    lister_profile = getattr(user, "lister_profile", None)

    if not lister_profile:
        return render(request, "lister/dashboard.html", {"todays_bookings": []})

    # Calculate approximate revenue
    approximate_revenue = 0
    completed_bookings = Booking.objects.filter(car__lister=lister_profile, status="COMPLETED")
    for booking in completed_bookings:
        if booking.start_date and booking.end_date:
            rental_days = (booking.end_date - booking.start_date).days
            approximate_revenue += rental_days * booking.car.price_per_day

    # Get today's date in the local timezone
    today = localtime(now()).date()

    # Fetch bookings created today using created_at
    todays_bookings = Booking.objects.filter(
        car__lister=lister_profile,
        created_at__date=today  # Filter by creation date
    ).order_by("-created_at")

    # Debugging: Log the count and data
    print(f"Bookings Created Today Count: {todays_bookings.count()}")
    for booking in todays_bookings:
        print(f"Booking: {booking.id}, Car: {booking.car}, Created At: {booking.created_at}")

    context = {
        "profile_exists": True,
        "total_cars": Car.objects.filter(lister=lister_profile).count(),
        "total_bookings": Booking.objects.filter(car__lister=lister_profile).count(),
        "approximate_revenue": approximate_revenue,
        "available_cars": Car.objects.filter(lister=lister_profile, available=True).count(),
        "bookings": completed_bookings,
        "todays_bookings": todays_bookings,
        "todays_bookings_count": todays_bookings.count(),  # For badge
    }

    return render(request, "lister/dashboard.html", context)


#This Section is for managing the lister's fleet of cars, allowing them to view, search, and paginate their car listings.👇


@login_required
@role_required("lister")
def manage_fleet(request):
    """ View for managing the lister’s fleet of cars """
    lister = request.user.lister_profile
    query = request.GET.get('q', '')

    # Filter cars based on search query and order by creation date
    cars = Car.objects.filter(lister=lister).filter(
        Q(make__icontains=query) | Q(model__icontains=query) | Q(vehicle_type__icontains=query)
    ).prefetch_related('images').order_by('-created_at')

    # Attach the first image for each car
    for car in cars:
        car.first_image = car.images.first().image.url if car.images.exists() else None

    # Paginate results (10 per page)
    paginator = Paginator(cars, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': query,
        'Car' :Car,
    }
    return render(request, 'lister/manage_fleet.html', context)


@login_required
@role_required("lister")
def car_availability_json(request, car_id):
    print("✅availability endpoint hit!")  # Debug line
    """ JSON endpoint for FullCalendar to fetch availability data """
    car = get_object_or_404(Car, id=car_id, lister=request.user.lister_profile)
    availabilities = car.availability.all()

    events = []
    for availability in availabilities:
        events.append({
            'title': 'Booked',
            'start': availability.start_date.isoformat(),
            'end': (availability.end_date + timedelta(days=1)).isoformat(),  # Exclusive end date for FullCalendar
        })

    print(f"Car ID: {car_id}, Availability Events Count: {len(events)}")    

    return JsonResponse(events, safe=False)



# Lister Functions HERE 👇 

@login_required
@role_required("lister")
@csrf_exempt
def create_or_update_lister_profile(request):
    """ Allows a lister to create or edit their profile """
    if request.method == "POST":
        user = request.user
        company_name = request.POST.get("company_name")
        contact_email = request.POST.get("contact_email")
        contact_phone = request.POST.get("contact_phone")
        whatsapp_number = request.POST.get("whatsapp_number")
        location = request.POST.get("location")

        # Check if profile exists
        try:
            profile = user.lister_profile
            profile.company_name = company_name
            profile.contact_email = contact_email
            profile.contact_phone = contact_phone
            profile.whatsapp_number = whatsapp_number
            profile.location = location
            profile.save()
            return JsonResponse({"message": "Profile updated successfully."})
        except ObjectDoesNotExist:
            # Create new profile
            ListerProfile.objects.create(
                user=user,
                company_name=company_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                whatsapp_number=whatsapp_number,
                location=location
            )
            return JsonResponse({"message": "Profile created successfully."})

    return JsonResponse({"error": "Invalid request method"}, status=405)



@login_required
@role_required("lister")
@require_POST
def create_car(request):
    """Handles car creation with images."""
    user = request.user

    try:
        lister = user.lister_profile
    except ListerProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found. Please create one."}, status=400)

    # Extract form data (NO NEED for json.loads)
    data = request.POST

    images = request.FILES.getlist("images")  # Extract uploaded images

    # Required fields validation
    required_fields = ["make", "model", "price_per_day"]
    for field in required_fields:
        if not data.get(field):
            return JsonResponse({"error": f"{field} is required."}, status=400)

    # Create car
    car = Car.objects.create(
        lister=lister,
        make=data["make"],
        model=data["model"],
        vehicle_type=data.get("vehicle_type"),
        seats=data.get("seats"),
        suitcases=data.get("suitcases"),
        doors=data.get("doors"),
        passengers=data.get("passengers"),
        transmission=data.get("transmission"),
        price_per_day=data["price_per_day"],
        least_days=data.get("least_days", 1),
        description=data.get("description", ""),
        available=data.get("available", "false").lower() == "true",  # Convert to boolean
    )

    # Save images
    if images:
        for image in images:
            CarImage.objects.create(car=car, image=image)

    return JsonResponse({"message": "Car listing created successfully!"}, status=201)


@login_required
@role_required("lister")
@require_POST
def edit_car(request, car_id):
    """Handles editing of a car listing, including images."""
    user = request.user
    try:
        lister = user.lister_profile
    except ListerProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found. Please create one."}, status=400)

    try:
        car = Car.objects.get(id=car_id, lister=lister)
    except Car.DoesNotExist:
        return JsonResponse({"error": "Car not found."}, status=404)

    # Use request.POST directly
    data = request.POST

    # Update fields only if provided
    for field in [
        "make", "model", "vehicle_type", "seats", "suitcases", "doors",
        "passengers", "transmission", "price_per_day", "least_days",
        "description"
    ]:
        if field in data:
            setattr(car, field, data[field])

    # Handle boolean field (checkbox issue)
    car.available = data.get("available") == "true"

    car.save()

    # Replace old images with new ones if provided
    images = request.FILES.getlist("images")
    if images:
        car.images.all().delete()  # Remove old images
        for image in images:
            CarImage.objects.create(car=car, image=image)

    return JsonResponse({"message": "Car details updated successfully!"}, status=200)


# Delete a car
@login_required
@role_required("lister")
@require_POST
def delete_car(request, car_id):
    """Handles deleting a car listing."""
    user = request.user
    try:
        lister = user.lister_profile
    except ListerProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found. Please create one."}, status=400)

    try:
        car = Car.objects.get(id=car_id, lister=lister)
    except Car.DoesNotExist:
        return JsonResponse({"error": "Car not found."}, status=404)

    car.delete()
    return JsonResponse({"message": "Car deleted successfully!"}, status=200)


@login_required
@role_required("lister")
@require_POST
def set_car_availability(request, car_id):
    print("✅ Set availability endpoint hit!")  # Debug line
    """Handles setting unavailable dates for a car."""
    user = request.user
    try:
        lister = user.lister_profile
    except ListerProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found. Please create one."}, status=400)

    try:
        car = Car.objects.get(id=car_id, lister=lister)
    except Car.DoesNotExist:
        return JsonResponse({"error": "Car not found."}, status=404)

    try:
        data = json.loads(request.body)
        start_date_str = data.get("start_date")  # e.g., "2025-04-16"
        end_date_str = data.get("end_date")      # e.g., "2025-04-18")

        if not start_date_str or not end_date_str:
            return JsonResponse({"error": "Both start and end dates are required."}, status=400)

        # Convert date strings to timezone-aware datetimes
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        start_date = timezone.make_aware(start_date)  # Make aware (uses TIME_ZONE or UTC)
        end_date = timezone.make_aware(end_date)      # Make aware

        CarAvailability.objects.create(car=car, start_date=start_date, end_date=end_date)
        return JsonResponse({"message": "Car availability updated successfully!"}, status=201)
    except ValueError as e:
        return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



# Respond to review

@login_required
@role_required("lister")
def respond_to_review(request, review_id):
    """ Allows a lister to respond to a review on their car """
    user = request.user

    try:
        review = RenterReview.objects.get(id=review_id)
    except RenterReview.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)

    # Check if the review is for the lister's car
    if review.car.lister != user.lister_profile:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method == "POST":
        comment_text = request.POST.get("comment", "").strip()

        if not comment_text:
            return JsonResponse({"error": "Comment cannot be empty"}, status=400)

        ReviewComment.objects.create(review=review, user=user, comment=comment_text)
        return JsonResponse({"message": "Reply added successfully"})

    return JsonResponse({"error": "Invalid request"}, status=400)



# This is the END of the manage fleet section for the lister Mada Fleka✌️


#THis section is for the booking management by a lister such as deleting, editing or viewing details Be warned👇


@login_required
@role_required("lister")
def manage_bookings(request):
    """View for managing bookings of listed cars"""
    lister = request.user.lister_profile
    bookings = Booking.objects.filter(car__lister=lister).order_by('-created_at')  # Sort by creation date

    # Pagination
    paginator = Paginator(bookings, 10)  # 10 bookings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'lister/manage_bookings.html', context)


@login_required
@role_required("lister")
def filter_bookings_json(request):
    """JSON endpoint to fetch filtered bookings"""
    lister = request.user.lister_profile
    filter_type = request.GET.get('filter', 'all')
    bookings = Booking.objects.filter(car__lister=lister).order_by('-created_at')

    today = timezone.now()

    if filter_type == 'today':
        bookings = bookings.filter(start_date__lte=today, end_date__gte=today)
    elif filter_type == 'monthly':
        current_month = today.month
        current_year = today.year
        bookings = bookings.filter(start_date__year=current_year, start_date__month=current_month)
    elif filter_type == 'yearly':
        current_year = today.year
        bookings = bookings.filter(start_date__year=current_year)

    # Serialize bookings with image URL
    booking_list = [
        {
            'id': booking.id,
            'car': f"{booking.car.make} {booking.car.model}",
            'renter': booking.renter.username,
            'start_date': booking.start_date.isoformat() if booking.start_date else None,
            'end_date': booking.end_date.isoformat() if booking.end_date else None,
            'pickup_location': booking.pickup_location,
            'return_location': booking.return_location,
            'total_cost': float(booking.total_cost) if booking.total_cost else 0.0,
            'status': booking.status,
            'created_at': booking.created_at.isoformat(),
            'car_image': booking.car.images.first().image.url if booking.car.images.exists() else None,
        }
        for booking in bookings
    ]

    return JsonResponse(booking_list, safe=False)


@login_required
@role_required("lister")
@require_POST
def edit_booking(request, booking_id):
    """API to edit a booking"""
    lister = request.user.lister_profile
    try:
        booking = Booking.objects.get(id=booking_id, car__lister=lister)
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found or you don’t have permission."}, status=404)

    data = json.loads(request.body)
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    pickup_location = data.get('pickup_location')
    return_location = data.get('return_location')
    total_cost = data.get('total_cost')
    status = data.get('status')

    # Update fields if provided
    if start_date:
        naive_start = timezone.datetime.fromisoformat(start_date)
        booking.start_date = timezone.make_aware(naive_start)  # Make it aware (default to UTC)
    if end_date:
        naive_end = timezone.datetime.fromisoformat(end_date)
        booking.end_date = timezone.make_aware(naive_end)      # Make it aware (default to UTC)
    if pickup_location:
        booking.pickup_location = pickup_location
    if return_location:
        booking.return_location = return_location
    if total_cost is not None:
        try:
            booking.total_cost = Decimal(total_cost)  # Convert string to Decimal
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid total cost format."}, status=400)
    if status in dict(Booking.STATUS_CHOICES):  # Validate status
        booking.status = status

    try:
        booking.clean()  # Run model validation
        booking.save()
        return JsonResponse({"message": "Booking updated successfully!"}, status=200)
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    

@login_required
@role_required("lister")
@require_POST
def delete_booking(request, booking_id):
    """API to delete a booking"""
    lister = request.user.lister_profile
    try:
        booking = Booking.objects.get(id=booking_id, car__lister=lister)
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Booking not found or you don’t have permission."}, status=404)

    booking.delete()
    return JsonResponse({"message": "Booking deleted successfully!"}, status=200)    


#  This is the END Of the bookings management by a lister Mada Fleka ✌️



@login_required
@role_required("lister")
def lister_profile(request):
    """ View for managing the lister’s profile """
    lister = request.user.lister_profile

    context = {
        'lister': lister,
    }
    return render(request, 'lister/Lister_profile.html', context)

@login_required
@role_required("lister")
def lister_reviews_complaints(request):
    """ Fetches all reviews and complaints related to the lister """
    user = request.user

    try:
        lister = user.lister_profile
    except ListerProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found. Please create one."}, status=400)

    # Fetch complaints where the lister is the accused
    complaints = Complaint.objects.filter(accused=user).order_by("-created_at")

    # Fetch reviews for the lister's cars
    reviews = RenterReview.objects.filter(car__lister=lister).order_by("-created_at")

    return render(request, "lister/reviews_complaints.html", {"complaints": complaints, "reviews": reviews})



# END OF LISTER VIEWS AND FUNCTIONALITIES #######################################################################


# Renter views and Functionalities HERE 👇 ##############################################################################
@block_listers
@csrf_exempt
def start(request):
    """
    Home page where renters enter:
    - Pickup & return locations
    - Pickup & return date & time
    - Data is passed via GET to car_list view
    """
        # Redirect listers to their dashboard if they try to access the start view
    if hasattr(request.user, 'listerprofile'):
        return redirect('lister_dashboard')  # Or use reverse('lister_dashboard')

    if request.method == "POST":
        pickup_location = request.POST.get("pickup_location")
        return_location = request.POST.get("return_location")
        pickup_date = request.POST.get("pickup_date")
        return_date = request.POST.get("return_date")
        pickup_time = request.POST.get("pickup_time")
        return_time = request.POST.get("return_time")

        # Redirect to car_list with necessary parameters
        return redirect(f"/cars/?pickup_location={pickup_location}&return_location={return_location}"
                        f"&pickup_date={pickup_date}&return_date={return_date}"
                        f"&pickup_time={pickup_time}&return_time={return_time}")

    return render(request, "renter/index.html")


@block_listers
def car_list(request):
    """ 
    Lists available cars based on:
    - Pickup & return date/time
    - Availability (ensuring no conflicts with existing CarAvailability records)
    - Minimum rental days (total_booking_days must be >= least_days)
    - Dynamic filters (vehicle type, gear shift, passengers)
    """
    pickup_location = request.GET.get("pickup_location")
    return_location = request.GET.get("return_location")
    pickup_date = request.GET.get("pickup_date")
    return_date = request.GET.get("return_date")
    pickup_time = request.GET.get("pickup_time")
    return_time = request.GET.get("return_time")

    # Validate required parameters
    if not all([pickup_location, return_location, pickup_date, return_date, pickup_time, return_time]):
        messages.error(request, "Missing booking details. Please start again.")
        return redirect("start")

    # Convert to datetime objects for filtering
    try:
        pickup_datetime = datetime.strptime(f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M")
        return_datetime = datetime.strptime(f"{return_date} {return_time}", "%Y-%m-%d %H:%M")
        pickup_datetime = timezone.make_aware(pickup_datetime)
        return_datetime = timezone.make_aware(return_datetime)
    except ValueError:
        messages.error(request, "Invalid date format. Please try again.")
        return redirect("start")

    # Calculate total booking days
    total_booking_days = (return_datetime - pickup_datetime).days
    if total_booking_days < 1:
        messages.error(request, "Booking duration must be at least 1 day.")
        return redirect("start")

    # Extract dates for comparison with CarAvailability
    pickup_date_only = pickup_datetime.date()
    return_date_only = return_datetime.date()

    # Get cars that are unavailable within the requested date range
    unavailable_car_ids = CarAvailability.objects.filter(
        Q(start_date__lte=return_date_only) & Q(end_date__gte=pickup_date_only)
    ).values_list("car_id", flat=True)

    # Filter available cars
    available_cars = Car.objects.exclude(id__in=unavailable_car_ids)

    # Filter cars where total_booking_days is greater than or equal to least_days
    available_cars = available_cars.filter(least_days__lte=total_booking_days).order_by('price_per_day')

    # Apply dynamic filters (vehicle type, gear shift, passengers)
    vehicle_type = request.GET.get('vehicle_type')
    if vehicle_type:
        available_cars = available_cars.filter(vehicle_type=vehicle_type)

    passengers = request.GET.get('passengers')
    if passengers:
        available_cars = available_cars.filter(passengers=passengers)

    transmission = request.GET.get('transmission')
    if transmission:
        available_cars = available_cars.filter(transmission=transmission)

    # Add pagination (9 cars per page)
    paginator = Paginator(available_cars, 9)  # 9 cars per page
    page_number = request.GET.get('page')  # Get the page number from the URL query
    page_obj = paginator.get_page(page_number)  # Get the specific page object

    # Pass choices from the Car model to the template
    vehicle_types = Car.VEHICLE_TYPE
    passengers_choices = Car.PASSENGERS_CHOICES
    transmission_choices = Car.TRANSMISSION_CHOICES

    return render(request, "renter/car_list.html", {
        "cars": page_obj,
        "pickup_location": pickup_location,
        "return_location": return_location,
        "pickup_date": pickup_date,
        "return_date": return_date,
        "pickup_time": pickup_time,
        "return_time": return_time,
        "vehicle_types": vehicle_types,
        "passengers_choices": passengers_choices,
        "transmission_choices": transmission_choices,
        "page_obj": page_obj,  # Pass page_obj for pagination controls
    })


@block_listers
@login_required
def car_booking(request, car_id):
    """Handles the car booking process."""
    car = get_object_or_404(Car, id=car_id)

    # Determine the source of booking details based on request method
    if request.method == "POST":
        pickup_location = request.POST.get("pickup_location")
        return_location = request.POST.get("return_location")
        pickup_date = request.POST.get("pickup_date")
        return_date = request.POST.get("return_date")
        pickup_time = request.POST.get("pickup_time")
        return_time = request.POST.get("return_time")
        total_cost = request.POST.get("total_cost")
    else:
        pickup_location = request.GET.get("pickup_location")
        return_location = request.GET.get("return_location")
        pickup_date = request.GET.get("pickup_date")
        return_date = request.GET.get("return_date")
        pickup_time = request.GET.get("pickup_time")
        return_time = request.GET.get("return_time")
        total_cost = None

    # Validate required parameters
    if not all([pickup_location, return_location, pickup_date, return_date, pickup_time, return_time]):
        print("Incomplete booking details. Please start again.")
        messages.error(request, "Incomplete booking details. Please start again.")
        return redirect("start")

    # Convert to datetime objects and make them aware
    try:
        pickup_datetime = datetime.strptime(f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M")
        return_datetime = datetime.strptime(f"{return_date} {return_time}", "%Y-%m-%d %H:%M")
        # Make the datetimes aware using the project's time zone
        pickup_datetime = timezone.make_aware(pickup_datetime)
        return_datetime = timezone.make_aware(return_datetime)
    except ValueError:
        print("Invalid date format. Please try again.")
        messages.error(request, "Invalid date format. Please try again.")
        return redirect("start")

    # Validate date range
    if pickup_datetime >= return_datetime:
        print("Return date must be after the pickup date.")
        messages.error(request, "Return date must be after the pickup date.")
        return redirect("start")

    # Calculate rental days and cost
    rental_days = (return_datetime - pickup_datetime).days
    if rental_days < 1:
        print("Minimum rental period is 1 day.")
        messages.error(request, "Minimum rental period is 1 day.")
        return redirect("start")

    if not total_cost:
        total_cost = rental_days * car.price_per_day
    else:
        total_cost = float(total_cost)

    # Base context with booking details
    context = {
        "car": car,
        "pickup_location": pickup_location,
        "return_location": return_location,
        "pickup_date": pickup_date,
        "return_date": return_date,
        "pickup_time": pickup_time,
        "return_time": return_time,
        "rental_days": rental_days,
        "total_cost": total_cost,
    }

    # Check if user has a ListerProfile but no RenterProfile
    if ListerProfile.objects.filter(user=request.user).exists() and not RenterProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Car owners cannot book cars as renters. Please create a renter profile.")
        query_params = (
            f"next=/cars/{car.id}/book/&"
            f"pickup_location={pickup_location}&"
            f"return_location={return_location}&"
            f"pickup_date={pickup_date}&"
            f"return_date={return_date}&"
            f"pickup_time={pickup_time}&"
            f"return_time={return_time}"
        )
        return redirect(f"/login/?{query_params}")

    # Check if user has a RenterProfile
    try:
        rental_profile = RenterProfile.objects.get(user=request.user)
    except RenterProfile.DoesNotExist:
        # Redirect to login page to create a profile
        query_params = (
            f"next=/cars/{car.id}/book/&"
            f"pickup_location={pickup_location}&"
            f"return_location={return_location}&"
            f"pickup_date={pickup_date}&"
            f"return_date={return_date}&"
            f"pickup_time={pickup_time}&"
            f"return_time={return_time}"
        )
        return redirect(f"/login/?{query_params}")

    context["rental_profile"] = rental_profile

    if request.method == "POST":
        try:
            # Convert total_cost to Decimal
            total_cost_decimal = decimal.Decimal(str(total_cost))

            # Create the booking with aware datetime objects
            booking = Booking.objects.create(
                renter=request.user,
                car=car,
                start_date=pickup_datetime,  # Now aware
                end_date=return_datetime,    # Now aware
                pickup_location=pickup_location,
                return_location=return_location,
                total_cost=total_cost_decimal,
                status="COMPLETED",
                created_at=timezone.now()  # Use timezone.now() instead of undefined now()
            )

            # Set session variable to indicate a new booking
            request.session["new_booking"] = True

            messages.success(request, "Booking successful! You are being Redirected To Chat with the Lister In a Few Minutes.")
            return redirect("booking_history")
        except Exception as e:
            print(f"Booking failed: {str(e)}")
            messages.error(request, f"Booking failed: {str(e)}")
            query_params = (
                f"pickup_location={pickup_location}&"
                f"return_location={return_location}&"
                f"pickup_date={pickup_date}&"
                f"return_date={return_date}&"
                f"pickup_time={pickup_time}&"
                f"return_time={return_time}"
            )
            return redirect(f"/cars/{car.id}/book/?{query_params}")

    return render(request, "renter/car_booking.html", context)


@block_listers
@login_required
@role_required("Renter")
def my_trips(request):
    """View for displaying the renter's booking history."""
    renter = request.user
    bookings = Booking.objects.filter(renter=renter).order_by("-created_at")  # Show latest bookings first

    # Retrieve and remove `new_booking` from session
    new_booking = request.session.pop("new_booking", False)

    # Get the car image URL for the most recent booking
    car_image_url = None
    if bookings.exists():
        recent_booking = bookings.first()
        # Get the first image for the car (assuming CarImage has a related_name='images')
        car_image = recent_booking.car.images.first()
        if car_image:
            # Build the absolute URL for the image
            car_image_url = request.build_absolute_uri(car_image.image.url)

    return render(request, "renter/my_trips.html", {
        "bookings": bookings,
        "new_booking": new_booking,
        "car_image_url": car_image_url,  # Pass the image URL to the template
    })


@block_listers
@login_required
@role_required("Renter")
def renter_profile(request):
    """View for displaying the renter's profile and booking history.""""""View for displaying the renter's profile and booking history."""
    print(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")  # Debug
    print(f"Request method: {request.method}")  # Debug
    renter = request.user
    try:
        profile = RenterProfile.objects.get(user=renter)
    except RenterProfile.DoesNotExist:
        profile = None

    # Fetch the user's bookings
    bookings = Booking.objects.filter(renter=renter).order_by("-created_at")

    return render(request, "renter/profile.html", {
        "renter": renter,
        "profile": profile,
        "bookings": bookings
    })


@csrf_exempt
@login_required
def create_renter_profile(request):
    """Creates a renter profile and returns a JSON response."""
    if request.method == "POST":
        user = request.user

        # Check if the user already has a profile
        if RenterProfile.objects.filter(user=user).exists():
            return JsonResponse({"success": False, "message": "Profile already exists."}, status=400)

        # Extract data from request
        id_image = request.FILES.get("id_image")
        driving_license_image = request.FILES.get("driving_license_image")
        whatsapp_number = request.POST.get("whatsapp_number")
        age = request.POST.get("age")

        # Log received data
        print(f"Received data - whatsapp_number: {whatsapp_number}, age: {age}")

        # Validate required fields
        if not age:
            return JsonResponse({"success": False, "message": "Age is required."}, status=400)

        # Validate WhatsApp number format (optional)
        import re
        if whatsapp_number and not re.match(r"^\+\d{10,15}$", whatsapp_number):
            return JsonResponse({"success": False, "message": "Invalid WhatsApp number format."}, status=400)

        # Save images if they exist
        id_image_path = None
        license_image_path = None

        if id_image:
            id_image_path = default_storage.save(f"id_images/{id_image.name}", id_image)

        if driving_license_image:
            license_image_path = default_storage.save(f"license_images/{driving_license_image.name}", driving_license_image)

        # Create profile
        renter_profile = RenterProfile.objects.create(
            user=user,
            id_image=id_image_path,
            driving_license_image=license_image_path,
            whatsapp_number=whatsapp_number,
            age=int(age),
            verification_status="PENDING"
        )

        return JsonResponse({
            "success": True,
            "message": "Profile created successfully.",
            "profile_id": renter_profile.id
        })

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)



@login_required
def update_renter_profile(request):
    """Updates an existing renter profile and returns a JSON response."""
    user = request.user
    renter_profile = get_object_or_404(RenterProfile, user=user)  # Get the profile or return 404

    if request.method == "POST":
        # Get updated fields from request
        whatsapp_number = request.POST.get("whatsapp_number")
        age = request.POST.get("age")
        id_image = request.FILES.get("id_image")
        driving_license_image = request.FILES.get("driving_license_image")

        # Update text fields if provided
        if whatsapp_number:
            renter_profile.whatsapp_number = whatsapp_number
        if age:
            renter_profile.age = int(age)

        # Handle new image uploads
        if id_image:
            id_image_path = default_storage.save(f"id_images/{id_image.name}", id_image)
            renter_profile.id_image = id_image_path

        if driving_license_image:
            license_image_path = default_storage.save(f"license_images/{driving_license_image.name}", driving_license_image)
            renter_profile.driving_license_image = license_image_path

        # Save the updated profile
        renter_profile.save()

        return JsonResponse({
            "success": True,
            "message": "Profile updated successfully."
        })

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)



# About Charge Car Rentals ###########################################################################

def about(request):
    featured_cars = Car.objects.all()
    context = {
        'featured_cars': featured_cars,
    }
    return render(request, "about/index_about.html", context)


from django.http import HttpResponse

def robots_txt(request):
    content = "User-agent: *\nAllow: /"
    return HttpResponse(content, content_type="text/plain")    