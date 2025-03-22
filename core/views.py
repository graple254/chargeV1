from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from core.auth import * # Import from auth.py
import time
from .decorators import role_required
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



# Authenications views and Functionalities HERE 👇 ##############################################################################



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


# END OF AUTHENTICATION VIEWS AND FUNCTIONALITIES #######################################################################


# Lister views and Functionalities HERE 👇 ##############################################################################


@login_required
@role_required("lister")
def lister_dashboard(request):
    """ Dashboard view for the car lister """
    user = request.user
    lister_profile = getattr(user, "lister_profile", None)  # Get profile or None

    context = {
        "profile_exists": bool(lister_profile),  # True if profile exists, False otherwise
        "total_cars": Car.objects.filter(lister=lister_profile).count() if lister_profile else 0,
        "total_bookings": Booking.objects.filter(car__lister=lister_profile).count() if lister_profile else 0,
        "pending_bookings": Booking.objects.filter(car__lister=lister_profile, status="PENDING").count() if lister_profile else 0,
    }

    return render(request, "lister/dashboard.html", context)


@login_required
@role_required("lister")
def manage_fleet(request):
    """ View for managing the lister’s fleet of cars """
    lister = request.user.lister_profile
    cars = Car.objects.filter(lister=lister)
    
    context = {
        'cars': cars,
    }
    return render(request, 'lister/manage_fleet.html', context)


@login_required
@role_required("lister")
def manage_bookings(request):
    """ View for managing bookings of listed cars """
    lister = request.user.lister_profile
    bookings = Booking.objects.filter(car__lister=lister)

    context = {
        'bookings': bookings,
    }
    return render(request, 'lister/manage_bookings.html', context)


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

# Lister Functions HERE 👇 

@login_required
@role_required("lister")
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



# Create a car
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

    data = json.loads(request.POST.get("data", "{}"))
    images = request.FILES.getlist("images")

    # Extract car details
    required_fields = ["make", "model", "price_per_day"]
    for field in required_fields:
        if not data.get(field):
            return JsonResponse({"error": f"{field} is required."}, status=400)

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
        available=data.get("available", True),
    )

    # Save images
    for image in images:
        CarImage.objects.create(car=car, image=image)

    return JsonResponse({"message": "Car listing created successfully!"}, status=201)


# Edit a car
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

    data = json.loads(request.POST.get("data", "{}"))
    images = request.FILES.getlist("images")

    # Update fields only if provided
    for field in [
        "make", "model", "vehicle_type", "seats", "suitcases", "doors",
        "passengers", "transmission", "price_per_day", "least_days",
        "description", "available"
    ]:
        if field in data:
            setattr(car, field, data[field])

    car.save()

    # Replace old images with new ones if provided
    if images:
        car.images.all().delete()
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


# Set car availability
@login_required
@role_required("lister")
@require_POST
def set_car_availability(request, car_id):
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

    data = json.loads(request.body)
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not start_date or not end_date:
        return JsonResponse({"error": "Both start and end dates are required."}, status=400)

    CarAvailability.objects.create(car=car, start_date=start_date, end_date=end_date)
    return JsonResponse({"message": "Car availability updated successfully!"}, status=201)



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



# END OF LISTER VIEWS AND FUNCTIONALITIES #######################################################################


# Renter views and Functionalities HERE 👇 ##############################################################################

def start(request):
    """
    Home page where renters enter:
    - Pickup & return locations
    - Pickup & return date & time
    - Data is passed via GET to car_list view
    """
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



def car_list(request):
    """ 
    Lists available cars based on:
    - Pickup & return date/time
    - Availability (ensuring no conflicts with existing bookings)
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
    except ValueError:
        messages.error(request, "Invalid date format. Please try again.")
        return redirect("start")

    # Exclude cars already booked in the requested date range
    unavailable_car_ids = Booking.objects.filter(
        start_date__lt=return_datetime,  
        end_date__gt=pickup_datetime
    ).values_list("car_id", flat=True)

    available_cars = Car.objects.exclude(id__in=unavailable_car_ids)

    return render(request, "renter/car_list.html", {
        "cars": available_cars,
        "pickup_location": pickup_location,
        "return_location": return_location,
        "pickup_date": pickup_date,
        "return_date": return_date,
        "pickup_time": pickup_time,
        "return_time": return_time,
    }) 


def car_booking(request, car_id):
    """Handles the car booking process."""
    car = get_object_or_404(Car, id=car_id)

    # Retrieve booking details from GET parameters
    pickup_location = request.GET.get("pickup_location")
    return_location = request.GET.get("return_location")
    pickup_date = request.GET.get("pickup_date")
    return_date = request.GET.get("return_date")
    pickup_time = request.GET.get("pickup_time")
    return_time = request.GET.get("return_time")

    # Validate required parameters
    if not all([pickup_location, return_location, pickup_date, return_date, pickup_time, return_time]):
        messages.error(request, "Incomplete booking details. Please start again.")
        return redirect("start")

    # Convert to datetime objects
    try:
        pickup_datetime = datetime.strptime(f"{pickup_date} {pickup_time}", "%Y-%m-%d %H:%M")
        return_datetime = datetime.strptime(f"{return_date} {return_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        messages.error(request, "Invalid date format. Please try again.")
        return redirect("start")

    # Validate date range
    if pickup_datetime >= return_datetime:
        messages.error(request, "Return date must be after the pickup date.")
        return redirect("start")

    # Ensure user is authenticated
    if not request.user.is_authenticated:
        return render(request, "renter/car_booking.html", {
            "car": car,
            "require_login": True,
        })

    # Ensure user has a rental profile
    try:
        rental_profile = RenterProfile.objects.get(user=request.user)
    except RenterProfile.DoesNotExist:
        return render(request, "renter/car_booking.html", {
            "car": car,
            "require_profile_creation": True,
        })

    # Calculate cost
    rental_days = (return_datetime - pickup_datetime).days
    if rental_days < 1:
        messages.error(request, "Minimum rental period is 1 day.")
        return redirect("start")

    total_cost = rental_days * car.price_per_day

    if request.method == "POST":
        try:
            Booking.objects.create(
                user=request.user,
                car=car,
                rental_profile=rental_profile,
                pickup_location=pickup_location,
                return_location=return_location,
                pickup_date=pickup_datetime,
                return_date=return_datetime,
                total_cost=total_cost,
                status="Pending",
                created_at=now()
            )
            messages.success(request, "Booking successful! Await confirmation.")
            return redirect("booking_confirmation")
        except Exception as e:
            messages.error(request, f"Booking failed: {str(e)}")
            return redirect(f"/car-booking/{car.id}/?pickup_location={pickup_location}&return_location={return_location}"
                            f"&pickup_date={pickup_date}&return_date={return_date}"
                            f"&pickup_time={pickup_time}&return_time={return_time}")

    return render(request, "renter/car_booking.html", {
        "car": car,
        "pickup_location": pickup_location,
        "return_location": return_location,
        "pickup_date": pickup_date,
        "return_date": return_date,
        "pickup_time": pickup_time,
        "return_time": return_time,
        "rental_profile": rental_profile,
        "total_cost": total_cost,
    })

@login_required
def my_trips(request):
    """ View for displaying the renter's booking history """
    renter = request.user
    bookings = Booking.objects.filter(renter=renter).order_by("-created_at")  # Show latest bookings first

    return render(request, "renter/my_trips.html", {"bookings": bookings})

@login_required
def renter_profile(request):
    """ View for displaying the renter's profile and booking history """
    renter = request.user
    bookings = Booking.objects.filter(renter=renter).order_by("-created_at")  # Show latest bookings first

    return render(request, "renter/profile.html", {"renter": renter, "bookings": bookings})


# renter functions

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

        # Validate required fields
        if not id_image or not driving_license_image or not age:
            return JsonResponse({"success": False, "message": "All required fields must be filled."}, status=400)

        # Save images properly
        id_image_path = default_storage.save(f"id_images/{id_image.name}", id_image)
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
