from django.urls import path
from .views import *

urlpatterns = [
    path("login/", authenticate_user, name="login"),
    path("send-verification-code/", send_verification_code, name="send_verification_code"),
    path("verify-email-code/", verify_email_code, name="verify_email_code"),
    path("signup/", user_signup, name="signup"),
    path("logout/", user_logout, name="logout"),
]