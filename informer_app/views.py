from django.http import HttpResponse
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import APIException

from .serializers import InfoPointSerializer
from .tasks import send_test_message, send_notifications
from .models import InfoPoint
from django.core.serializers import serialize


class InfoPointNotFound(APIException):
    status_code = 400
    default_detail = 'Info point with this id not found'
    default_code = 'bad_request'

class NotificationView(ListAPIView, APIView):
    permission_classes = [IsAuthenticated]
    queryset = InfoPoint.objects.all()

    def get_object(self, *args, **kwargs):
        try:
            return InfoPoint.objects.get(pk=kwargs['pk'], user=kwargs['user'])
        except InfoPoint.DoesNotExist:
            raise InfoPointNotFound

    def post(self, request, *args, **kwargs):
        serializer = InfoPointSerializer(context = {'request':request},data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        infopoint = self.get_object(pk=pk, user=request.user)
        infopoint.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        # Note the use of `get_queryset()` instead of `self.queryset`
        user = self.request.user
        queryset = self.get_queryset().filter(user=user)
        serializer = CustomGeoJSONSerializer()
        serializer.serialize(queryset, fields=('name', 'id'), geometry_field='point')
        # Response ставил везде обратные слеши Http их не ставит
        return HttpResponse(serializer.getvalue(), content_type='application/json')

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
