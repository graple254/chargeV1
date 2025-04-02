from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import *

@receiver(post_save, sender=Booking)
def create_availability(sender, instance, created, **kwargs):
    if created:
        CarAvailability.objects.create(
            car=instance.car,
            start_date=instance.start_date,
            end_date=instance.end_date
        )
 
@receiver(post_delete, sender=Booking)
def remove_availability(sender, instance, **kwargs):
    CarAvailability.objects.filter(
        car=instance.car,
        start_date=instance.start_date,
        end_date=instance.end_date
    ).delete()
