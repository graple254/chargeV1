from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

class AuthTests(TestCase):
    def setUp(self):
        """Setup test client and create a test user"""
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123"
        )

    def test_authenticate_user_valid(self):
        """Test login with valid credentials"""
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "TestPassword123"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "success", "message": "Login successful!", "user": "testuser"})

    def test_authenticate_user_invalid(self):
        """Test login with incorrect credentials"""
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "WrongPassword"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "error", "message": "Invalid credentials"})

    def test_send_verification_code(self):
        """Test sending an email verification code"""
        response = self.client.post(reverse("send_verification_code"), {"email": "newuser@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": True, "message": "Verification code sent!"})

    def test_verify_correct_code(self):
        """Test email verification with correct code"""
        session = self.client.session
        session["email_verification_code"] = "123456"
        session["email_verification_address"] = "newuser@example.com"
        session.save()

        response = self.client.post(reverse("verify_email_code"), {"code": "123456"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": True, "message": "Email verified successfully!"})

    def test_verify_wrong_code(self):
        """Test email verification with incorrect code"""
        session = self.client.session
        session["email_verification_code"] = "123456"
        session["email_verification_address"] = "newuser@example.com"
        session.save()

        response = self.client.post(reverse("verify_email_code"), {"code": "654321"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": False, "error": "Invalid verification code"})

    def test_signup_verified_email(self):
        """Test signup with a verified email"""
        session = self.client.session
        session["verified_email"] = "newuser@example.com"
        session.save()

        response = self.client.post(reverse("signup"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "phone_number": "123456789",
            "role": "renter",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": True, "user": "newuser"})

    def test_signup_unverified_email(self):
        """Test signup without verifying email"""
        response = self.client.post(reverse("signup"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "phone_number": "123456789",
            "role": "renter",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123"
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": False, "error": "Email not verified"})

    def test_user_logout(self):
        """Test user logout"""
        self.client.login(username="testuser", password="TestPassword123")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": True})




