from django.contrib import admin

from auth_app.models import Person


@admin.register(Person)
class AuthAppAdmin(admin.ModelAdmin):
    pass


from django.contrib import admin

# Register your models here.
