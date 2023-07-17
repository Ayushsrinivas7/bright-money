from django.db import models

# Create your models here.
class UserInformation(models.Model):

    TRANSACTION_TYPES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit')
    ]

    user_id = models.TextField(max_length=100)
    date = models.DateTimeField(auto_now_add=False)
    amount = models.FloatField(default=0.0)
    transaction_type = models.CharField(max_length=8, choices=TRANSACTION_TYPES)
    