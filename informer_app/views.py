from django.http import HttpResponse
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import InfoPointSerializer
from .tasks import send_test_message, send_notifications
from .models import InfoPoint
from django.core.serializers import serialize


class CreateNotificationView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InfoPointSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(status=status.HTTP_201_CREATED)


class InfoPointsList(ListAPIView):
    queryset = InfoPoint.objects.all()
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # Note the use of `get_queryset()` instead of `self.queryset`
        user = self.request.user
        queryset = self.get_queryset().filter(user=user)
        #serializer = InfoPointSerializer(queryset, many=True)
        return HttpResponse(serialize('geojson', queryset, fields=('name', 'id,'), geometry_field='point'))


def check_intersection(request):
    #send_notifications()
    send_test_message()
    return HttpResponse('ok')
