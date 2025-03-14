from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings



# Visitor model tracks new visitors to our site.  👇 ###############################################################################################################

class Visitor(models.Model):
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True, null=True)
    visit_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Visitor {self.ip_address} on {self.visit_date}"
    

# User differentiates between renters and listers  👇 ################################################################################

class User(AbstractUser):
    ROLE_CHOICES = (
        ('RENTER', 'Renter'),
        ('LISTER', 'Lister'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
    


# Renter models 👇 ###################################################################################################################

class RenterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='renter_profile')
    id_image = models.ImageField(upload_to='id_images/')
    driving_license_image = models.ImageField(upload_to='license_images/')
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)

    VERIFICATION_CHOICES = (
        ('PENDING', 'Pending'),
        ('DISCREPANT', 'Discrepant'),
        ('VERIFIED', 'Verified'),
    )
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_CHOICES, default='PENDING')

    def __str__(self):
        return f"Renter Profile: {self.user.username} ({self.verification_status})"


class Complaint(models.Model):
    filer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_complaints')
    accused = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_complaints')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint by {self.filer.username} against {self.accused.username}"


class RenterReview(models.Model):
    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    car = models.ForeignKey('Car', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.renter.username} for {self.car}"


class ReviewComment(models.Model):
    review = models.ForeignKey(RenterReview, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_lister(self):
        return self.review.car.lister == self.user

    def __str__(self):
        return f"Comment by {self.user.username} on review {self.review.id}"


# Lister models for the car rental companies  👇 #####################################################################################


# Lister Profile - Stores details about the car rental business
class ListerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lister_profile')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    contact_email = models.EmailField(unique=True, blank=True, null=True)
    contact_phone = models.CharField(max_length=15, unique=True, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    verified = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self):
        return f"Business: {self.company_name} ({self.user.username})"


# Car - Represents a car listed for rent
class Car(models.Model):
    lister = models.ForeignKey(ListerProfile, on_delete=models.CASCADE, related_name='cars')
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    least_days = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year}) - {self.lister.company_name}"


# Car Image - Allows multiple images per car
class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='car_images/')

    def __str__(self):
        return f"Image for {self.car.make} {self.car.model}"


# Car Features - Stores optional features per car
class CarFeature(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='features')
    feature_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.feature_name} - {self.car.make} {self.car.model}"


# Car Availability - Defines unavailable dates for a car
class CarAvailability(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='availability')
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"Unavailable: {self.car.make} {self.car.model} ({self.start_date} - {self.end_date})"


# Booking - Tracks rental details

class Booking(models.Model):
    renter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def clean(self):
        if self.start_date < timezone.now().date():
            raise ValidationError("Start date cannot be in the past.")
        if self.end_date < self.start_date:
            raise ValidationError("End date must be after the start date.")

    def save(self, *args, **kwargs):
        self.clean()  # Ensure validation runs before saving
        super().save(*args, **kwargs)


# this are like the rules set by the car lister
class BookingOverview(models.Model):
    lister = models.OneToOneField(ListerProfile, on_delete=models.CASCADE, related_name='booking_overview')
    third_party_insurance = models.BooleanField(default=True)
    breakdown_assistance = models.BooleanField(default=True)
    loss_damage_waiver = models.TextField(help_text="Details about financial responsibility for damages and theft.")

    def __str__(self):
        return f"Booking Overview for {self.lister.company_name}"




# Lister Earnings - Tracks earnings for listers
class ListerEarnings(models.Model):
    lister = models.OneToOneField(ListerProfile, on_delete=models.CASCADE, related_name='earnings')
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Earnings for {self.lister.company_name}: ${self.total_earnings}"