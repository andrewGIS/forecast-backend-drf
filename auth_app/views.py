from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User
from .serializers import RegisterSerializer
from rest_framework import generics


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


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
