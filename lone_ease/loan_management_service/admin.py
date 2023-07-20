from django.contrib import admin

from .models import UserInformation, UserTransactionInformation, LoanInfo, EMIDetails

# Register your models here.
admin.site.register(UserInformation)
admin.site.register(UserTransactionInformation)
admin.site.register(LoanInfo)
admin.site.register(EMIDetails)

