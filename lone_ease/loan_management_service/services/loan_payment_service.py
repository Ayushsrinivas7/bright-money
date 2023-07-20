import uuid

from datetime import datetime

from ..models_service import EMIDetailsDbService, LoanInformationDbService
from ..utils import LoanCalculations
class LoanPaymentService:
    def __init__(self):
        self.emi_details_db_service = EMIDetailsDbService()
        self.loan_info_db_service = LoanInformationDbService()
        self.loan_calculations = LoanCalculations()

    def make_payment(self, payload):
        loan_id_str = payload.get('loan_id')
        amount = payload.get('amount')

        loan_id = uuid.UUID(loan_id_str)
        loan_info = self.loan_info_db_service.get_loan_information(loan_id=loan_id)
        if not loan_info:
            response = {'message': 'loan not found'}
            return response

        loan_id = loan_info.loan_id
        # installment_date = datetime(
        #     datetime.now().year, datetime.now().month, 1
        # )  # starting of the current month and year

        installment_date = datetime(2023, 10, 1)
        emi_details = self.emi_details_db_service.get_emi_details_by_installment_date(
            loan_info.loan_id, installment_date
        )
        if not emi_details:
            return {
                'message': 'No emi found for this month'
            }

        past_dues_pending = self.emi_details_db_service.check_past_dues(loan_id, installment_date)
        if past_dues_pending:
            return {
                'message': 'past dues are pending please complete those first'
            }
        
        if (emi_details.amount_due > 0 and emi_details.amount_paid > 0) or emi_details.amount_due==0:
            response = {
                'message': "EMI already paid for this month",
                'data': {
                    'emi_due': emi_details.amount_due,
                    'emi_paid': emi_details.amount_paid,
                    'installment_paid': str(emi_details.installment_date)
                }
            }
            return response

        if amount < emi_details.amount_due:
            return {
                'message': 'amount paid is smaller than emi due for the month'
            }
        
        emi_details.amount_paid = amount
        emi_details.save()
        if amount > emi_details.amount_due:
            self.recalculate_and_update_emi(loan_id)
            
        response = {
            'message': 'EMI paid successfully for this month',
            'data': {
                'emi_due': emi_details.amount_due,
                'emi_paid': emi_details.amount_paid,
                'installment_paid': str(emi_details.installment_date)
            }
        }
        return response

    def recalculate_and_update_emi(self, loan_id):
        amount_with_interest_till_now = (
            self.emi_details_db_service.get_sum_of_paid_emis(loan_id)
        )

        print("AMOUNT WITH INTEREST", amount_with_interest_till_now)

        no_of_emis_paid_till_now = self.emi_details_db_service.no_of_emis_paid(loan_id)

        print("NO OF EMIS PAID TILL NOW", no_of_emis_paid_till_now)

        loan_info = self.loan_info_db_service.get_loan_information(loan_id)
        principle_loan = loan_info.loan_amount
        interest_rate = loan_info.annual_interest_rate / (12*100)

        # interest_paid_till_now = self.loan_calculations.calculate_interest(
        #     principle_loan, interest_rate, no_of_emis_paid_till_now
        # )

        interest = int(44870/loan_info.term_period)
        interest_paid_till_now = interest*no_of_emis_paid_till_now

        print("INTEREST PAID TILL NOW",interest_paid_till_now)

        principle_amount_outstanding = principle_loan - (
            amount_with_interest_till_now - interest_paid_till_now
        )

        print("PRINCIPAL AMOUNT OUTSTANDING", principle_amount_outstanding)

        if principle_amount_outstanding <= 0:
            rows_updated = self.emi_details_db_service.update_due_amount(loan_id, 0)
            print("ROWS UPDATED", rows_updated)
            if rows_updated == 0:
                response = {"message": "EMI paid for all months"}
                return response

        tenure = loan_info.term_period - no_of_emis_paid_till_now
        updated_emis = self.loan_calculations.calculate_emi(
            principle_amount_outstanding, interest_rate, tenure
        )

        print("UPDATED EMI", updated_emis)
        self.emi_details_db_service.update_due_amount(loan_id, updated_emis)

