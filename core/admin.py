from django.contrib import admin
from .models import *
# Register your models here.


# Custom action to bulk verify renters
def verify_renters(modeladmin, request, queryset):
    queryset.update(verification_status='VERIFIED')
verify_renters.short_description = "Mark selected renters as Verified"

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("visit_date", "location")
    list_filter = ("visit_date", "location")
    search_fields = ("location", "visit_date")


# User Admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')

# Renter Profile Admin
@admin.register(RenterProfile)
class RenterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_status', 'age', 'whatsapp_number')
    list_filter = ('verification_status',)
    search_fields = ('user__username', 'user__email')
    actions = [verify_renters]  # Add bulk verification action

# Complaint Admin
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('filer', 'accused', 'created_at')
    search_fields = ('filer__username', 'accused__username')
    list_filter = ('created_at',)

# Renter Review Admin
@admin.register(RenterReview)
class RenterReviewAdmin(admin.ModelAdmin):
    list_display = ('renter', 'car', 'rating', 'created_at')
    search_fields = ('renter__username', 'car__name')
    list_filter = ('rating', 'created_at')

# Review Comment Admin
@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'review', 'created_at')
    search_fields = ('user__username', 'review__renter__username')
    list_filter = ('created_at',)



# Lister admin management 👇 ###################################################################################################################

# Bulk verification action
def verify_listers(modeladmin, request, queryset):
    queryset.update(verified=True)
verify_listers.short_description = "Mark selected listers as verified"


@admin.register(ListerProfile)
class ListerProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_email', 'contact_phone', 'location', 'verified')
    search_fields = ('company_name', 'contact_email', 'contact_phone')
    list_filter = ('verified', 'location')
    actions = [verify_listers]


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'year', 'price_per_day', 'lister', 'available')
    search_fields = ('make', 'model', 'lister__company_name')
    list_filter = ('available', 'year')


@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    list_display = ('car', 'image')


@admin.register(CarFeature)
class CarFeatureAdmin(admin.ModelAdmin):
    list_display = ('feature_name', 'car')


@admin.register(CarAvailability)
class CarAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('car', 'start_date', 'end_date')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('renter', 'car', 'start_date', 'end_date', 'status', 'created_at')
    search_fields = ('renter__username', 'car__make', 'car__model')
    list_filter = ('status', 'start_date', 'end_date')


@admin.register(BookingOverview)
class BookingOverviewAdmin(admin.ModelAdmin):
    list_display = ('lister', 'third_party_insurance', 'breakdown_assistance')


@admin.register(ListerEarnings)
class ListerEarningsAdmin(admin.ModelAdmin):
    list_display = ('lister', 'total_earnings', 'last_updated')

