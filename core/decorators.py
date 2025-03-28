from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(role):
    """Decorator to restrict access to users with a specific role."""
    def decorator(view_func):
        @wraps(view_func)  # Preserves function metadata
        def _wrapped_view(request, *args, **kwargs):
            user_role = getattr(request.user, "role", None)  # Safely get role

            # Normalize the role names for comparison
            expected_role = role.strip().upper()
            current_role = user_role.strip().upper() if user_role else None

            print(f"User role: '{current_role}' (Type: {type(user_role)})")
            print(f"Expected role: '{expected_role}' (Type: {type(role)})")

            if current_role != expected_role:
                print("Permission denied: User role does not match.")
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
