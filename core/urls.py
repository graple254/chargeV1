from django.urls import path
from .views import *

urlpatterns = [
    # User Authentication Endpoints
    path("login/", authenticate_user, name="login"),
    path("send-verification-code/", send_verification_code, name="send_verification_code"),
    path("verify-email-code/", verify_email_code, name="verify_email_code"),
    path("signup/", user_signup, name="signup"),
    path("logout/", logout_user, name="logout"),
    path("create_profile/", create_renter_profile, name="create_profile"),
    path("edit_profile/", update_renter_profile, name="edit_profile"),
    path("check-auth-status/", check_auth_status, name="check_auth_status"),

    
    # Lister Endpoints
    path('dashboard/', lister_dashboard, name='lister_dashboard'),
    path('manage-fleet/', manage_fleet, name='manage_fleet'),
    path('manage-bookings/', manage_bookings, name='manage_bookings'),
    path('profile/', lister_profile, name='lister_profile'),
    path("reviews&Complaints/", lister_reviews_complaints, name="lister_reviews_complaints"),


    # Lister Profile Management
    path("profile/update/", create_or_update_lister_profile, name="update_lister_profile"),

    # Car Management
    path("cars/create/", create_car, name="create_car"),
    path("cars/<int:car_id>/edit/", edit_car, name="edit_car"),
    path("cars/<int:car_id>/delete/", delete_car, name="delete_car"),

    # Car Availability
    path("cars/<int:car_id>/availability/", set_car_availability, name="set_car_availability"),


    # Reviews and Complaints
    path('reviews/respond/<int:review_id>/', respond_to_review, name='respond_to_review'),


    # Renter Endpoints and VIEWS
    path("", start, name="start"),  
    path("cars/", car_list, name="car_list"),
    path("cars/<int:car_id>/book/", car_booking, name="car_booking"),
    path("bookings/", my_trips, name="booking_history"),
    path("renter_profile/", renter_profile, name="renter_profile"),
]