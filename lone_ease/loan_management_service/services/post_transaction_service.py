from ..models_service import EMIDetailsDbService, LoanInformationDbService

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
                'installment_date': str(transaction.installment_date)
            }
            past_transactions_list.append(info)

        upcoming_transactions_list = []
        for transaction in upcoming_transactions:
            info = {
                'amount_due': transaction.amount_due,
                'installment_date': str(transaction.installment_date)
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