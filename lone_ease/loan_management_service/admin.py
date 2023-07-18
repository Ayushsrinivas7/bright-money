from django.contrib import admin
from .models import UserInformation, UserTransactionInformation

# Register your models here.
admin.site.register(UserInformation)
admin.site.register(UserTransactionInformation)