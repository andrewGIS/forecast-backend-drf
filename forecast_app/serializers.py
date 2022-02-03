from rest_framework import serializers

from .models import ForecastModel, ForecastGroup, Calculation


class ForecastModelSerializer(serializers.BaseSerializer):
    data = {"models": ForecastModel.objects.all().values_list('name', flat=True)}



class CalculationSerializer(serializers.BaseSerializer):
    #data = {"groups": Calculation.objects.all().values_list('forecast_group__name', 'forecast_group__alias')}

    def to_representation(self, instance):
        return {'name': instance.forecast_group.name, 'alias': instance.forecast_group.alias}




# class ForecastGroupSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ForecastGroup
#         fields = ('name', 'alias')


class ForecastGroupSerializer(serializers.RelatedField):
    def to_representation(self, value: ForecastGroup):
        return str({'name': value.name, 'alias': value.alias})


# class CalculationSerializer(serializers.ModelSerializer):
#     group = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Calculation
#         fields = ('group',)
#
#     def get_group(self, instance):
#         return {'name': instance.forecast_group.name, 'alias': instance.forecast_group.alias}
