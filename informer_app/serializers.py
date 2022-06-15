from rest_framework import serializers
from django.contrib.gis.geos import Point
from informer_app.models import InfoPoint

from django.core import serializers as DjangoSerializers
GeoJSONSerializer = DjangoSerializers.get_serializer("geojson")
class CustomGeoJSONSerializer(GeoJSONSerializer):
    """
    Add ID to feature properties
    """
    def get_dump_object(self, obj):
        data = super(CustomGeoJSONSerializer, self).get_dump_object(obj)
        # Extend to your taste
        data['properties']['id']=obj.pk
        return data

class InfoPointSerializer(serializers.ModelSerializer):

    X = serializers.FloatField(required=True, write_only=True)
    Y = serializers.FloatField(required=True, write_only=True)
    name = serializers.CharField(required=True, write_only=True)
    pointFromUTCOffset = serializers.IntegerField(required=True, write_only=True)

    class Meta:
        model = InfoPoint
        fields = ('X', 'Y', 'name', 'pointFromUTCOffset')

    def create(self, validated_data):
        pnt = Point(
            x=float(validated_data['X']),
            y=float(validated_data['Y']),
            srid=4326
        )
        infoPoint = InfoPoint(
            user=self.context['request'].user,
            point=pnt,
            name=validated_data['name'],
            pointFromUTCOffset=validated_data['pointFromUTCOffset']
        )
        infoPoint.save()

        return infoPoint

