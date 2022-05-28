from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password

from auth_app.models import Person
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterSerializer(serializers.ModelSerializer):
    telegram_login = serializers.CharField(
        required=False,
        # validators=[UniqueValidator(queryset=User.objects.all())]
    )
    # username = serializers.CharField(
    #     required=True,
    #     validators=[UniqueValidator(queryset=User.objects.all())]
    # )
    # password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    username = serializers.CharField(required=True, source='user.username')
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    first_name = serializers.CharField(required=True, source='user.first_name')
    last_name = serializers.CharField(required=True, source='user.last_name')

    class Meta:
        model = Person
        fields = ('username', 'first_name', 'last_name', 'password', 'telegram_login')

    # def validate(self, attrs):
    #     if attrs['password'] != attrs['password2']:
    #         raise serializers.ValidationError({"password": "Password fields didn't match."})
    #
    #     return attrs
    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['user']['username'],
            first_name=validated_data['user']['first_name'],
            last_name=validated_data['user']['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()

        person = Person.objects.create(user=user, telegram_login=validated_data['telegram_login'])
        person.save()

        return person

