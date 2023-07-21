from datetime import datetime
from ..constants import LOAN_BOUNDS, SUPPORTED_LOAN_TYPES, USER_INCOME_FOR_LOAN, THRESHOLD_INTEREST_RATE, THRESHOLD_INTEREST_AMOUNT, MIN_CREDIT_SCORE
from ..models_service import (EMIDetailsDbService, LoanInformationDbService,
                              UserInformationDbService)
from ..utils import LoanCalculations



class LoanApplicationService:
    def __init__(self) -> None:
        self.user_information_db_service = UserInformationDbService()
        self.loan_info_db_service = LoanInformationDbService()
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_calculations = LoanCalculations()

    def is_loan_applicable(
        self, user, loan_type, loan_amount, interest_rate, term_period
    ):
        if user.credit_score < MIN_CREDIT_SCORE:
            return {
                'message': 'credit score below threshold value'
            }
        if loan_type not in SUPPORTED_LOAN_TYPES:
            return {
                'message': 'loan type not supported'
            }
        
        loan_bound_amount = LOAN_BOUNDS[loan_type]
        if loan_amount > loan_bound_amount:
            return {
                'message': f'loan amount is out of bounds'
            }

        elif user.annual_income < USER_INCOME_FOR_LOAN:
            return {
                'message': 'user income below income limit to apply for loan'
            }

        elif interest_rate < THRESHOLD_INTEREST_RATE:
            return {
                'message': 'interest below the threshold interest rate'
            }

        monthly_interest = interest_rate/(100*12)
        EMI_due = self.loan_calculations.calculate_emi(
            loan_amount, monthly_interest, term_period
        )

        interest_amount = self.loan_calculations.calculate_compound_interest(loan_amount, interest_rate/100, term_period)
        if interest_amount <= THRESHOLD_INTEREST_AMOUNT:
            return {
                'message': 'interest amount below threshold amount'
            }

        monthly_income = user.annual_income // 12
        if EMI_due > 0.6 * monthly_income:
            return {
                'message': 'EMI due is more than 60% of the monthly income'
            }

        return {
            'message': 'Loan is Applicable',
            'data': {
                'emi_due': EMI_due
                }
            }

    def apply_loan(self, payload):
        user_uuid = payload.get("user_uuid")
        loan_type = payload.get("loan_type")
        loan_amount = payload.get("loan_amount")
        interest_rate = payload.get("interest_rate")
        term_period = payload.get("term_period")
        disbursement_date = payload.get("disbursement_date")

        disbursement_date_obj = datetime.strptime(disbursement_date, "%Y-%m-%d")

        user = self.user_information_db_service.get_user_by_uuid(user_uuid=user_uuid)
        response = {}
        if not user:
            return {
                'message': 'user is not registered' 
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
            loan_id = self.loan_info_db_service.create_entry(
                user.user_uuid,
                loan_type,
                loan_amount,
                interest_rate,
                term_period,
                disbursement_date_obj,
            )

            emi_due = response['data']['emi_due']

            self.emi_details_db_service.save_emi_details(
                loan_id, emi_due, disbursement_date_obj, term_period
            )

            emi_dues_information = self.emi_details_db_service.get_emi_details_by_loan_id(loan_id)

            data = {'EMI_details': []}
            data['loan_id'] = str(loan_id)
            for emi in emi_dues_information:
                information = {
                    'amount_due': emi.amount_due,
                    'amount_paid': emi.amount_paid,
                    'installment_date': str(emi.installment_date),
                }
                data['EMI_details'].append(information)


            response = {
                'message': 'loan applied successfuly',
                'data': data
            }
            return response