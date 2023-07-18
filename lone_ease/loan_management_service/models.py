from django.db import models

# Create your models here.
class UserInformation(models.Model):

    name = models.CharField(max_length=128)
    email = models.CharField(max_length=64)
    annual_income = models.FloatField()
    aadhar_id = models.CharField(max_length=64,unique=True)

class UserTransactionInformation(models.Model):

    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit')
    ]

    user_id = models.ForeignKey(UserInformation, on_delete=models.CASCADE, to_field='aadhar_id')
    date = models.DateTimeField(auto_now_add=False)
    amount = models.FloatField(default=0.0)
    transaction_type = models.CharField(max_length=8, choices=TRANSACTION_TYPES)
    
    