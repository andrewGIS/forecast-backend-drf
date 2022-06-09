from django.http import HttpResponse
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer


def check_jwt(request):
    JWT_authenticator = JWTAuthentication()

    # authenitcate() verifies and decode the token
    # if token is invalid, it raises an exception and returns 401
    response = JWT_authenticator.authenticate(request)
    if response is not None:
        # unpacking
        print(response)
        user, token = response
        print (user, token['user_id'])
        user_id = token['user_id']
        user = User.objects.get(id=user_id)
        return HttpResponse("this is decoded token claims", token.payload)
    else:
        return HttpResponse("no token is provided in the header or the header is missing")


class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        refresh = RefreshToken.for_user(serializer.instance.user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
