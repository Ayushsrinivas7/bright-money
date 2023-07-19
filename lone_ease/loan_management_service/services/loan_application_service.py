from datetime import datetime

from ..constants import LOAN_BOUNDS, SUPPORTED_LOAN_TYPES, USER_INCOME_FOR_LOAN
from ..models_service import (EMIDetailsDbService, LoanInformationDbService,
                              UserInformationDbService,
                              UserTransactionInformation)
from ..utils import LoanCalculations


class UserRegistrationService:
    def __init__(self):
        self.user_information_db_service = UserInformationDbService()
        self.user_transaction_db_service = UserTransactionInformation()

    def register_user(self, payload):
        aadhar_id = payload.get("aadhar_id")
        name = payload.get("name")
        email_id = payload.get("email_id")
        annual_income = payload.get("annual_income")

        # registering a user
        # also check if user already registered
        user = UserInformation.objects.create(
            name=name, email=email_id, annual_income=annual_income, aadhar_id=aadhar_id
        )

        # calculating credit score which will be invoked in a celery task further
        user = UserInformation.objects.filter(aadhar_id=11223344).first()
        total_credit = UserTransactionInformation.objects.filter(
            user_id=user.aadhar_id, transaction_type="CREDIT"
        ).aggregate(total_amount=Sum("amount"))
        total_debit = UserTransactionInformation.objects.filter(
            user_id=user.aadhar_id, transaction_type="DEBIT"
        ).aggregate(total_amount=Sum("amount"))

        total_credit_amount = int(total_credit["total_amount"])
        total_debit_amount = int(total_debit["total_amount"])

        total_account_balance = total_credit_amount - total_debit_amount
        credit_score = 0
        if (
            total_account_balance <= ACCOUNT_BALANCE_CONFIG["MIN_VALUE"]
        ):  # value to be stored in config
            credit_score = CREDIT_SCORE_CONFIG["MIN_SCORE"]
        elif total_account_balance >= ACCOUNT_BALANCE_CONFIG["MAX_VALUE"]:
            credit_score = CREDIT_SCORE_CONFIG["MAX_SCORE"]
        else:
            balance_change = ACCOUNT_BALANCE_CONFIG["BALANCE_CHANGE"]
            increment = ACCOUNT_BALANCE_CONFIG["INCREMENT"]
            credit_score = (total_account_balance // balance_change) + increment


class LoanApplicationService:
    def __init__(self) -> None:
        self.user_information_db_service = UserInformationDbService()
        self.loan_info_db_service = LoanInformationDbService()
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_calculations = LoanCalculations()

    def is_loan_applicable(
        self, user, loan_type, loan_amount, interest_rate, term_period, is_valid=False
    ):
        response = {}
        if loan_type not in SUPPORTED_LOAN_TYPES:
            response["message"] = "loan type not supported"
            return response

        loan_bound_amount = LOAN_BOUNDS[loan_type]
        if loan_amount > loan_bound_amount:
            response["message"] = f"loan amount is out of bounds for {loan_type} loan"
            return response

        elif user.annual_income >= USER_INCOME_FOR_LOAN:
            response["message"] = "user income below income limit to apply for loan"

        elif interest_rate <= 14:
            response["message"] = "interest below the threshold rate"

        # check and return

        interest = self.loan_calculations.calculate_interest(
            loan_amount, interest_rate, term_period
        )
        if interest < 10000:
            response["message"] = "interest amount below threshold"

        EMI_due = self.loan_calculations.calculate_emi(
            loan_amount, interest_rate / 12, term_period
        )
        monthly_income = user.annual_income / 12
        if EMI_due > 0.6 * monthly_income:
            response["message"] = "EMI due is more than 60% of the monthly income"

        return response

    def apply_loan(self, payload):
        user_uuid = payload.get("user_uuid")
        loan_type = payload.get("loan_type")
        loan_amount = payload.get("loan_amount")
        interest_rate = payload.get("interest_rate")
        term_period = payload.get("term_period")
        disbursement_date = payload.get("disbursement_date")

        user = self.user_information_db_service.get_user_by_uuid(user_uuid=user_uuid)
        response = {}
        if user is None:
            response["message"] = "user is not registered"

        response = self.is_loan_applicable(
            user, loan_type, loan_amount, interest_rate, term_period
        )

        if not response["is_loan_applicable"]:
            pass
        else:
            loan_id = self.loan_info_db_service.create_entry(
                user.user_uuid,
                loan_type,
                loan_amount,
                interest_rate,
                term_period,
                disbursement_date,
            )

            emi_due = 0
            self.emi_details_db_service.save_emi_details(
                loan_id, emi_due, disbursement_date, term_period
            )

            emi_dues_information = self.emi_details_db_service.get_emi_details(loan_id)

            response = {}
            for emi in emi_dues_information:
                information = {
                    "amount_due": emi.amount_due,
                    "amount_paid": emi.amount_paid,
                    "installment_date": emi.installment_date,
                }
                response["EMI_Details"].append(information)

            response["loan_id"]: loan_id
            return response


class LoanPaymentService:
    def __init__(self) -> None:
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_info_db_service = LoanInformationDbService()
        self.loan_calculations = LoanCalculations()

    def make_payment(self, payload):
        loan_id = payload.get("loan_id")
        amount = payload.get("amount")

        loan_info = self.loan_info_db_service.get_loan_information(loan_id=loan_id)
        if not loan_info:
            response = {"message": "loan not found"}
            return response

        loan_id = loan_info.loan_id
        installment_date = datetime(
            datetime.now().year, datetime.now().month, 1
        )  # starting of the current month and year

        emi_details = self.emi_details_db_service.get_emi_details_by_installment_date(
            loan_info.loan_id, installment_date
        )

        if emi_details.amount_due > 0 and emi_details.amount_paid > 0:
            response = {
                "message": "EMI already paid for this month",
                "data": emi_details.installment_date,
            }
            return response

        self.emi_details_db_service.update_paid_amount(
            loan_id, amount, installment_date
        )
        if amount >= emi_details.amount_due:
            # recalculate the emi's for the next months
            # calculate the interest and principal amount
            # update emi for every entry after the current entry
            # if emi's due are zero update the amount_due to 0 for the next entries
            self.recalculate_and_update_emi(loan_id)
        response = {
            "message": "EMI paid successfully for this month",
            "data": emi_details,
        }
        return

    def recalculate_and_update_emi(self, loan_id):
        amount_with_interest_till_now = (
            self.emi_details_db_service.get_sum_of_paid_emis(loan_id)
        )
        no_of_emis_paid_till_now = self.emi_details_db_service.no_of_emis_paid(loan_id)

        loan_info = self.loan_info_db_service.get_loan_information(loan_id)
        principle_loan = loan_info.loan_amount
        interest_rate = loan_info.annual_interest_rate / 12

        interest_paid_till_now = self.loan_calculations.calculate_interest(
            principle_loan, interest_rate, no_of_emis_paid_till_now
        )

        principle_amount_outstanding = principle_loan - (
            amount_with_interest_till_now - interest_paid_till_now
        )
        if principle_amount_outstanding == 0:
            rows_updated = self.emi_details_db_service.update_due_amount(loan_id, 0)
            if rows_updated == 0:
                response = {"message": "EMI paid for all months"}
                return response

        tenure = loan_info.tenure - no_of_emis_paid_till_now
        updated_emis = self.loan_calculations.calculate_emi(
            principle_amount_outstanding, interest_rate, tenure
        )

        self.emi_details_db_service.update_due_amount(loan_id, updated_emis)
