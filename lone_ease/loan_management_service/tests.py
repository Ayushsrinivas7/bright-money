import uuid


from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.test import TestCase, Client
from urllib.parse import urlencode

from .models import UserInformation, UserTransactionInformation, LoanInfo, EMIDetails

# Create your tests here.
class TestLoanManagementService(TestCase):

    def test_send_msg(self):

        data = {
            "aadhar_id":123456789, 
            "name": "akshat",
            "email_id": "akshat@test.com",
            "annual_income": 1500000
            }

        transaction_obj_1 = UserTransactionInformation.objects.create(aadhar_id=data["aadhar_id"], registration_date=datetime.now(), amount=50000, transaction_type="DEBIT")
        transaction_obj_2 = UserTransactionInformation.objects.create(aadhar_id=data["aadhar_id"], registration_date=datetime.now(), amount=100000, transaction_type="CREDIT")
        transaction_obj_3 = UserTransactionInformation.objects.create(aadhar_id=data["aadhar_id"], registration_date=datetime.now(), amount=100000, transaction_type="CREDIT")

        c = Client()
        response = c.post(path="/register_user/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, 200) 
        
        user_uuid_str = response.json()["data"]["user_uuid"]
        user_uuid = uuid.UUID(user_uuid_str)

        self.assertIsNotNone(user_uuid)

        user_object = UserInformation.objects.filter(user_uuid=user_uuid).first()
        self.assertIsNotNone(user_object)
        self.assertEqual(user_object.credit_score, 311)

 
    def test_apply_loan(self):

        user = UserInformation.objects.create(name="akshat", email="akshat@test.com", annual_income=1500000, aadhar_id=123456789, credit_score=500)
        c = Client()

        data = {
                "user_uuid":str(user.user_uuid),
                "loan_type":"ELECTRONICS",
                "loan_amount":100000,
                "interest_rate":15,
                "term_period":10,
                "disbursement_date":"2023-07-19"
            }
        response = c.post(path="/apply_loan/", data=data, content_type="application/json")
        self.assertEqual(response.json()["success"], "False")
        self.assertEqual(response.json()["message"], "Loan not applicable -> loan type not supported")

        data = {
                "user_uuid":str(user.user_uuid),
                "loan_type":"CAR",
                "loan_amount":800000,
                "interest_rate":15,
                "term_period":10,
                "disbursement_date":"2023-07-19"
            }
        response = c.post(path="/apply_loan/", data=data, content_type="application/json")
        self.assertEqual(response.json()["success"], "False")
        self.assertEqual(response.json()["message"], "Loan not applicable -> loan amount is out of bounds")
        
        data = {
                "user_uuid":str(user.user_uuid),
                "loan_type":"CAR",
                "loan_amount":600000,
                "interest_rate":13,
                "term_period":10,
                "disbursement_date":"2023-07-19"
            }
        response = c.post(path="/apply_loan/", data=data, content_type="application/json")
        self.assertEqual(response.json()["success"], "False")
        self.assertEqual(response.json()["message"], "Loan not applicable -> interest below the threshold interest rate")

        data = {
                "user_uuid":str(user.user_uuid),
                "loan_type":"CAR",
                "loan_amount":600000,
                "interest_rate":16,
                "term_period":6,
                "disbursement_date":"2023-07-19"
            }
        response = c.post(path="/apply_loan/", data=data, content_type="application/json")
        self.assertEqual(response.json()["success"], "False")
        self.assertEqual(response.json()["message"], "Loan not applicable -> EMI due is more than 60% of the monthly income")

        data = {
                "user_uuid":str(user.user_uuid),
                "loan_type":"CAR",
                "loan_amount":100000,
                "interest_rate":15,
                "term_period":6,
                "disbursement_date":"2023-07-19"
            }
        response = c.post(path="/apply_loan/", data=data, content_type="application/json")
        self.assertEqual(response.json()["success"], "False")
        self.assertEqual(response.json()["message"], "Loan not applicable -> interest amount below threshold amount")
        
        data = {
                "user_uuid":str(user.user_uuid),
                "loan_type":"CAR",
                "loan_amount":600000,
                "interest_rate":16,
                "term_period":10,
                "disbursement_date":"2023-07-19"
            }

        response = c.post(path="/apply_loan/", data=data, content_type="application/json")
        self.assertEqual(response.json()["success"], "True")

        loan_id_str = response.json()['data']['loan_id']
        loan_id = uuid.UUID(loan_id_str)
        loan_info = LoanInfo.objects.filter(loan_id=loan_id).first()
        self.assertIsNotNone(loan_info)
        
        emi_count = EMIDetails.objects.filter(loan_id_id=loan_id).count()
        self.assertGreater(emi_count, 0)
        self.assertEqual(emi_count, loan_info.term_period)

    def test_make_payment(self):

        user = UserInformation.objects.create(name="akshat", email="akshat@test.com", annual_income=1500000, aadhar_id=123456789)
        disbursement_date = datetime(datetime.now().year, datetime.now().month, datetime.now().day)-relativedelta(months=1)

        loan_info = LoanInfo.objects.create(user_uuid_id=user.user_uuid, loan_type="CAR", loan_amount=600000, annual_interest_rate=16, term_period=10, disbursement_date=disbursement_date)
        emi_due = 64201
        installment_date =  datetime(datetime.now().year, datetime.now().month, 1)
        emi_details_obj = EMIDetails.objects.create(loan_id_id=loan_info.loan_id, amount_due=emi_due, installment_date=installment_date)

        data = {
            "loan_id": str(loan_info.loan_id),
            "amount": emi_due
        }

        c = Client()
        response = c.post(path="/make_payment/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        response_status = response.json()['success']
        emi_paid = response.json()["data"]['emi_paid']

        self.assertEqual(response_status, "True")
        self.assertGreater(emi_paid, 0)

        c = Client()
        response = c.post(path="/make_payment/", data=data, content_type="application/json")
        response_status = response.json()['success']
        response_message = response.json()['message']

        self.assertEqual(response_status,"True")
        self.assertEqual(response_message, "EMI already paid for this month")


    def test_get_statement(self):
        
        user = UserInformation.objects.create(name="akshat", email="akshat@test.com", annual_income=1500000, aadhar_id=123456789)
        disbursement_date = datetime(datetime.now().year, datetime.now().month, datetime.now().day)-relativedelta(months=1)

        loan_info = LoanInfo.objects.create(user_uuid_id=user.user_uuid, loan_type="CAR", loan_amount=600000, annual_interest_rate=16, term_period=10, disbursement_date=disbursement_date)
        emi_due = 64201
        installment_date_1 = datetime(datetime.now().year, datetime.now().month, 1)
        installment_date_2 = installment_date_1 + relativedelta(months=1)
        installment_date_3 = installment_date_2 + relativedelta(months=2)

        emi_details_1 = EMIDetails.objects.create(loan_id_id=loan_info.loan_id, amount_due=emi_due, amount_paid=emi_due, installment_date=installment_date_1)
        emi_details_2 = EMIDetails.objects.create(loan_id_id=loan_info.loan_id, amount_due=emi_due, amount_paid=emi_due, installment_date=installment_date_2)
        emi_details_3 = EMIDetails.objects.create(loan_id_id=loan_info.loan_id, amount_due=emi_due, installment_date=installment_date_3)

        params = {
            "loan_id": str(loan_info.loan_id)
        }
        encoded_params = urlencode(params)
        c = Client()
        response = c.get(path=f"/get_statement/?{encoded_params}")
        due_emi_count = len(response.json()["data"]["upcoming_transactions"])
        paid_emi_count = len(response.json()["data"]["past_transactions"])
        
        self.assertEqual(paid_emi_count, 2)
        self.assertEqual(due_emi_count, 1)
