import requests
from django.utils.deprecation import MiddlewareMixin
from .models import Visitor, ListerProfile
from django.urls import reverse
from django.shortcuts import redirect

class VisitorTrackingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip_address = self.get_client_ip(request)
        location = self.get_location(ip_address)
        
        # Check if the visitor already exists
        if not Visitor.objects.filter(ip_address=ip_address).exists():
            Visitor.objects.create(ip_address=ip_address, location=location)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_location(self, ip_address):
        try:
            response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
            data = response.json()
            if data.get('status') == 'fail':
                return 'Unknown'
            return f"{data.get('city')}, {data.get('country')}"
        except requests.exceptions.RequestException as e:
            return 'Unknown'


class RoleRedirectMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            # Check if user has a ListerProfile
            is_lister = ListerProfile.objects.filter(user=request.user).exists()

            # Only redirect on specific pages (e.g., the main landing/start page)
            # Prevent infinite redirect loops by excluding the lister_dashboard itself
            if is_lister and request.path in [reverse('start'), reverse('about')]:  # adjust as needed
                return redirect('lister_dashboard')

        return None

class BlockListersFromRenterViewsMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Only apply to authenticated users with a ListerProfile
        if request.user.is_authenticated and hasattr(request.user, "listerprofile"):
            # Paths or view names to block for listers
            blocked_paths = [
                reverse("start"),
                reverse("car_booking", kwargs={"car_id": 1}).replace("1", ""),  # strip ID for path match
                reverse("booking_history"),
                reverse("car_list"),
            ]

            request_path = request.path

            if any(request_path.startswith(path) for path in blocked_paths):
                return redirect("lister_dashboard")

            # Optional: Check by view_func.__name__ instead of URL
            blocked_views = ["start", "car_booking", "my_trips", "car_list"]
            if view_func.__name__ in blocked_views:
                return redirect("lister_dashboard")

        return None  # continue as normal        

