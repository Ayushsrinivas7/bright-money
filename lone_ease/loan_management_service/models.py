import uuid

from django.db import models


# Create your models here.
class UserInformation(models.Model):
    name = models.CharField(max_length=128)
    email = models.CharField(max_length=64)
    annual_income = models.FloatField()
    aadhar_id = models.CharField(max_length=64, unique=True)
    credit_score = models.IntegerField(default=0)
    user_uuid = models.UUIDField(default=uuid.uuid4, unique=True)


class UserTransactionInformation(models.Model):
    TRANSACTION_TYPES = [("CREDIT", "Credit"), ("DEBIT", "Debit")]

    aadhar_id = models.ForeignKey(
        UserInformation, on_delete=models.CASCADE, to_field="aadhar_id"
    )
    registration_date = models.DateTimeField(auto_now_add=False)
    amount = models.FloatField(default=0.0)
    transaction_type = models.CharField(max_length=8, choices=TRANSACTION_TYPES)


class LoanInfo(models.Model):
    loan_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user_uuid = models.ForeignKey(
        UserInformation, on_delete=models.CASCADE, to_field="user_uuid"
    )
    loan_type = models.CharField(max_length=64)
    loan_amount = models.IntegerField(default=0)
    annual_interest_rate = models.FloatField()
    term_period = models.IntegerField(default=0)
    disbursement_date = models.DateTimeField()


class EMIDetails(models.Model):
    loan_id = models.ForeignKey(LoanInfo, on_delete=models.CASCADE, to_field="loan_id")
    amount_due = models.FloatField(default=None)
    amount_paid = models.FloatField(default=0.0)
    installment_date = models.DateTimeField()
