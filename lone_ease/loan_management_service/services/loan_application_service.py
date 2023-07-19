from datetime import datetime

from ..constants import LOAN_BOUNDS, SUPPORTED_LOAN_TYPES, USER_INCOME_FOR_LOAN, ACCOUNT_BALANCE_CONFIG, CREDIT_SCORE_CONFIG
from ..models_service import (EMIDetailsDbService, LoanInformationDbService,
                              UserInformationDbService,
                              UserTransactionInformationDbService)
from ..utils import LoanCalculations


class UserRegistrationService:
    def __init__(self):
        self.user_information_db_service = UserInformationDbService()
        self.user_transaction_db_service = UserTransactionInformationDbService()

    def register_user(self, payload):
        aadhar_id = payload.get("aadhar_id")
        name = payload.get("name")
        email_id = payload.get("email_id")
        annual_income = payload.get("annual_income")

        # registering a user
        is_user_exist = self.user_information_db_service.get_user_by_aadhar(aadhar_id)
        if is_user_exist:
            return {'message': 'User already exists'}
        # also check if user already registered
        user = self.user_information_db_service.create_user(name, email_id, annual_income, aadhar_id)

        # calculating credit score which will be invoked in a celery task further
        response = self.calculate_credit_score(user.aadhar_id)
        if response.get('message'):
            return {
                'message': 'user successfully registered',
                'data': {
                    'user_uuid': user.user_uuid
                }}
        else:
            return {'message': 'Not able to calculate credit score'}
        
    def calculate_credit_score(self, aadhar_id):

        
        total_credit = self.user_transaction_db_service.get_transactions_sum(aadhar_id, "CREDIT")
        total_debit = self.user_transaction_db_service.get_transactions_sum(aadhar_id, "DEBIT")

        total_credit_amount = int(total_credit["total_amount"])
        total_debit_amount = int(total_debit["total_amount"])

        total_account_balance = total_credit_amount-total_debit_amount
        credit_score = 0
        if total_account_balance <= ACCOUNT_BALANCE_CONFIG["MIN_VALUE"]:
            credit_score = CREDIT_SCORE_CONFIG["MIN_SCORE"]
        elif total_account_balance >= ACCOUNT_BALANCE_CONFIG["MAX_VALUE"]:
            credit_score = CREDIT_SCORE_CONFIG["MAX_SCORE"]
        else:
            balance_change = ACCOUNT_BALANCE_CONFIG["BALANCE_CHANGE"]
            increment = ACCOUNT_BALANCE_CONFIG["INCREMENT"]
            credit_score = (total_account_balance // balance_change) + increment
        
        self.user_information_db_service.save_credit_score(aadhar_id, credit_score)

        return {'message': 'credit score calculated and stored'}

class LoanApplicationService:
    def __init__(self) -> None:
        self.user_information_db_service = UserInformationDbService()
        self.loan_info_db_service = LoanInformationDbService()
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_calculations = LoanCalculations()

    def is_loan_applicable(
        self, user, loan_type, loan_amount, interest_rate, term_period
    ):
        response = {}
        if loan_type not in SUPPORTED_LOAN_TYPES:
            return {
                'message': 'loan type not supported'
            }
        
        loan_bound_amount = LOAN_BOUNDS[loan_type]
        if loan_amount > loan_bound_amount:
            return {
                'message': f'loan amount is out of bounds for {loan_type} loan'
            }

        elif user.annual_income >= USER_INCOME_FOR_LOAN:
            return {
                'message': 'user income below income limit to apply for loan'
            }

        elif interest_rate <= 14:
            return {
                'message': 'interest below the threshold rate'
            }
    
        if interest < 10000:
            response["message"] = "interest amount below threshold"

        EMI_due = self.loan_calculations.calculate_emi(
            loan_amount, interest_rate / 12, term_period
        )
        interest = loan_amount-EMI_due

        if interest < 10000:
            return {
                'message': 'interest amount below threshold'
            }

        monthly_income = user.annual_income / 12
        if EMI_due > 0.6 * monthly_income:
            return {
                'message': 'EMI due is more than 60% of the monthly income'
            }

        return {
            'message': 'Loan is Applicable',
            'data': {
                'emi_due': EMI_due,
                'interest_amount': interest
                }
            }

    def apply_loan(self, payload):
        user_uuid = payload.get("user_uuid")
        loan_type = payload.get("loan_type")
        loan_amount = payload.get("loan_amount")
        interest_rate = payload.get("interest_rate")
        term_period = payload.get("term_period")
        disbursement_date = payload.get("disbursement_date")

        user = self.user_information_db_service.get_user_by_uuid(user_uuid=user_uuid)
        response = {}
        if user:
            return {
                'message': 'user is already registered' 
            }

        response = self.is_loan_applicable(
            user, loan_type, loan_amount, interest_rate, term_period
        )

        if not response.get('data'):
            reason = response['message']
            return {
                'message': f'Loan not applicable -> {reason}'
            }
        else:
            loan_info = self.loan_info_db_service.create_entry(
                user.user_uuid,
                loan_type,
                loan_amount,
                interest_rate,
                term_period,
                disbursement_date,
            )

            emi_due = response['emi_due']
            loan_id = loan_info.loan_id

            self.emi_details_db_service.save_emi_details(
                loan_id, emi_due, disbursement_date, term_period
            )

            emi_dues_information = self.emi_details_db_service.get_emi_details_by_loan_id(loan_id)

            data = {}
            for emi in emi_dues_information:
                information = {
                    'amount_due': emi.amount_due,
                    'amount_paid': emi.amount_paid,
                    'installment_date': emi.installment_date,
                }
                data['EMI_Details'].append(information)

            data['loan_id']: loan_id

            response = {
                'message': 'loan applied successfuly',
                'data': data
            }
            return response


class LoanPaymentService:
    def __init__(self):
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_info_db_service = LoanInformationDbService()
        self.loan_calculations = LoanCalculations()

    def make_payment(self, payload):
        loan_id = payload.get('loan_id')
        amount = payload.get('amount')

        loan_info = self.loan_info_db_service.get_loan_information(loan_id=loan_id)
        if not loan_info:
            response = {'message': 'loan not found'}
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
                'message': "EMI already paid for this month",
                'data': {
                    'emi_due': emi_details.amount_due,
                    'installment_paid': emi_details.installment_date
                }
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
            'message': 'EMI paid successfully for this month',
            'data': {
                'emi_due': emi_details.amount_due,
                'emi_paid': emi_details.amount_paid,
                'installment_paid': emi_details.installment_date
            }
        }
        return response

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

class PostTransactionService:

    def __init__(self) -> None:
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_info_db_service = LoanInformationDbService()

    def get_transaction_statement(self, loan_id):

        loan_info = self.loan_info_db_service.get_loan_information(loan_id)

        if not loan_info:
            return {
                'message': 'no loan has been applied'
            }

        past_transactions = self.emi_details_db_service.get_paid_emi_details(loan_id=loan_info.loan_id) 
        upcoming_transactions = self.emi_details_db_service.get_unpaid_emi_details(loan_id=loan_info.loan_id)

        past_transactions_list = []
        for transaction in past_transactions:
            info = {
                'amount_paid': transaction.amount_paid,
                'installment_date': transaction.installment_date
            }
            past_transactions_list.append(info)

        upcoming_transactions_list = []
        for transaction in upcoming_transactions:
            info = {
                'amount_due': transaction.amount_due,
                'installment_date': transaction.installment_date
            }
            upcoming_transactions_list.append(info)
    
        response = {
            'message': 'success',
            'data': {
                'upcoming_transactions': upcoming_transactions_list,
                'past_transactions': past_transactions_list
            }
        }
        return response