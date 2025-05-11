from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .serializers import (
    UserRegistrationSerializer,
    VerifyEmailSerializer,
    UserLoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .utils import send_verification_email, send_password_reset_email

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        send_verification_email(user)

        return Response({
            "message": "User registered successfully. Please check your email for verification.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_201_CREATED)


class EmailVerificationView(APIView):
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            user = User.objects.get(verification_token=token)

            if user.verification_token_expires < timezone.now():
                send_verification_email(user)
                return Response({
                    "message": "Verification token expired. A new token has been sent to your email."
                }, status=status.HTTP_400_BAD_REQUEST)

            user.is_verified = True
            user.verification_token = None
            user.verification_token_expires = None
            user.save()

            return Response({
                "message": "Email verified successfully."
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                "message": "Invalid token."
            }, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.filter(email=email).first()

        if user is None or not user.check_password(password):
            return Response({
                "message": "Invalid email or password."
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_verified:
            # Send verification email again
            send_verification_email(user)
            return Response({
                "message": "Email not verified. A verification email has been sent to your email."
            }, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful.",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            },
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({
                "message": "Logout successful."
            }, status=status.HTTP_200_OK)
        except TokenError:
            return Response({
                "message": "Invalid token."
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()

        if user:
            send_password_reset_email(user)

        return Response({
            "message": "If a user with this email exists, a password reset link has been sent."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(reset_password_token=token)

            if user.reset_password_token_expires < timezone.now():
                send_password_reset_email(user)
                return Response({
                    "message": "Password reset token expired. A new token has been sent to your email."
                }, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(password)
            user.reset_password_token = None
            user.reset_password_token_expires = None
            user.save()

            return Response({
                "message": "Password reset successful."
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                "message": "Invalid token."
            }, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            user = User.objects.get(email=request.data['email'])
            response.data['user'] = {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }

        return response


class CustomTokenRefreshView(TokenRefreshView):
    pass