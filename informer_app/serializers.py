from rest_framework import serializers
from django.contrib.gis.geos import Point
from informer_app.models import InfoPoint


class InfoPointSerializer(serializers.ModelSerializer):

    X = serializers.FloatField(required=True, write_only=True)
    Y = serializers.FloatField(required=True, write_only=True)
    name = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = InfoPoint
        fields = ('X', 'Y', 'name')

    def create(self, validated_data):
        pnt = Point(x=float(validated_data['X']), y=float(validated_data['Y']), srid=4326)
        infoPoint = InfoPoint(
            user=self.context['request'].user,
            point=pnt,
            name=validated_data['name'],
        )
        infoPoint.save()

        return infoPoint
