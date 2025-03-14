from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


# Visitor model tracks new visitors. ###############################################################################################################

class Visitor(models.Model):
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=255, blank=True, null=True)
    visit_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Visitor {self.ip_address} on {self.visit_date}"
    

# User differentiates between renters and listers ################################################################################

class User(AbstractUser):
    ROLE_CHOICES = (
        ('RENTER', 'Renter'),
        ('LISTER', 'Lister'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"