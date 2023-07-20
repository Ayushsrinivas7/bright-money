from ..models_service import UserInformationDbService, UserTransactionInformationDbService
from ..tasks import calculate_credit_score

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
        response = calculate_credit_score.delay(user)
       
        response = {
                    'message': 'user successfully registered',
                    'data': {
                        'user_uuid': user.user_uuid
                    }}
        
        return response