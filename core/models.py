from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile



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
    id_image = models.ImageField(upload_to='id_images/', null=True, blank=True)
    driving_license_image = models.ImageField(upload_to='license_images/', null=True, blank=True)
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
    contact_email = models.EmailField(unique=True, blank=True, null=True)
    contact_phone = models.CharField(max_length=15, unique=True, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    verified = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self):
        return f"Business: {self.company_name} ({self.user.username})"


# Car - Represents a car listed for rent
class Car(models.Model):
    VEHICLE_TYPE = (
        ('Minivan', 'Minivan'),
        ('SUV', 'Suv'),
        ('SMALL CAR', 'Small Car'),
        ('Medium Car', 'Medium Car'),
        ('Pickup Truck', 'Pickup Truck'),
        ('Luxury', 'Luxury'),
        ('Van/Bus', 'Van/Bus'),
        ('Electric car', 'Electric car'),
    )
    PASSENGERS_CHOICES = (
        ('2+', '2+'),
        ('4+', '4+'),
        ('5+', '5+'),
        ('7+', '7+'),
    )
    TRANSMISSION_CHOICES = (
        ('AUTOMATIC', 'Automatic'),
        ('MANUAL', 'Manual'),
    )
    lister = models.ForeignKey(ListerProfile, on_delete=models.CASCADE, related_name='cars')
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPE, blank=True, null=True)
    seats = models.PositiveIntegerField(blank=True, null=True)
    suitcases = models.PositiveIntegerField(blank=True, null=True)
    doors = models.PositiveIntegerField(blank=True, null=True)
    passengers = models.CharField(max_length=20, choices=PASSENGERS_CHOICES, blank=True, null=True)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, blank=True, null=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    least_days = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.make} {self.model} - {self.lister.company_name}"


# Car Image - Allows multiple images per car
class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='car_images/')

    def save(self, *args, **kwargs):
        # Open image
        img = Image.open(self.image)
        
        # Resize while maintaining aspect ratio
        target_size = (752, 500)
        img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Save image back to the file
        img_io = BytesIO()
        img.save(img_io, format='JPEG', quality=85)  # Adjust quality for optimization
        self.image = ContentFile(img_io.getvalue(), name=self.image.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.car.make} {self.car.model}"



# Car Availability - Defines unavailable dates for a car
class CarAvailability(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='availability')
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Unavailable: {self.car.make} {self.car.model} ({self.start_date} - {self.end_date})" 


#Booking - Represents a booking made by a renter for a car
class Booking(models.Model):
    renter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    pickup_location = models.CharField(max_length=255, blank=True, null=True)
    return_location = models.CharField(max_length=255, blank=True, null=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='COMPLETED')

    def clean(self):
        # Check if start_date is in the past, comparing datetime to datetime
        if self.start_date and self.start_date < timezone.now():
            raise ValidationError("Start datetime cannot be in the past.")
        # Check if end_date is before start_date
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End datetime must be after the start datetime.")
        # Check if total_cost is valid
        if self.total_cost is not None and self.total_cost <= 0:
            raise ValidationError("Total cost must be greater than zero.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking: {self.car} by {self.renter.username} from {self.start_date} to {self.end_date}"



# this are like the rules set by the car lister
class BookingOverview(models.Model):
    lister = models.OneToOneField(ListerProfile, on_delete=models.CASCADE, related_name='booking_overview')
    third_party_insurance = models.BooleanField(default=True)
    breakdown_assistance = models.BooleanField(default=True)
    loss_damage_waiver = models.TextField(help_text="Details about financial responsibility for damages and theft.")
    renter_age = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Booking Overview for {self.lister.company_name}"




# Lister Earnings - Tracks earnings for listers
class ListerEarnings(models.Model):
    lister = models.OneToOneField(ListerProfile, on_delete=models.CASCADE, related_name='earnings')
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Earnings for {self.lister.company_name}: ${self.total_earnings}"