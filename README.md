# Chat Support
### Requirements

- Python 3.6.8
- Django==3.2.11
- django-extensions==3.1.0
- ipython==7.13.0
- requests==2.27.1
- pytest==7.0.1


### Steps to run

1. clone the github repo - git clone https://github.com/akshat302/bright-money.git
2. cd into the Branch-International folder - cd bright-money/lone_ease
3. run python manage.py migrate in the terminal.
4. run python manage.py runserver in the terminal to run the server.
5. To run test corresponding to the API's run `python manage.py test` in the terminal.

### Entities 

1. Message

### Database Models

UserInformation:

	name: name of the user (Assumed to be unique)
	email: email of the user
	annual_income: annual_income of the user
	aadhar_id: aadhar_id of the user which is a unique field
	credit_score: credit score of the user
	user_uuid: unique uuid generated for each registered user

UserTransactionInformation

  	aadhar_id: aadhar_id of the user
  	registration_date: transaction registration date
  	amount: transaction amount
  	transaction_type: type of transaction either DEBIT or CREDIT
  	credit_score: credit score of the user

LoanInfo

    loan_id: unique uuid generated to identify the loan
    user_uuid: uuid field which is a foreign key to UserInformation's user_uuid field
    loan_type: type of loan applied
    loan_amount: loan amount in rupees
    annual_interest_rate: annual rate of interest for the loan applied
    term_period: term period of repayment of the loan in months
    disbursement_date: date of disbursement of loan

 EMIDetails
 
    loan_id: loan_id of the loan for which EMIs are generated which is a foreign key to LoanInfo loan_id field 
    amount_due: EMI due each month in rupees
    amount_paid: EMI paid each month in rupees
    installment_date: date of installment of EMI
  
### API Details 

register_user -

    URL - "http://127.0.0.1:8000/register_user/"
    Type - POST
    Request Body - {
                    "aadhar_id":123456789, 
                    "name": "akshat",
                    "email_id": "akshat@test.com",
                    "annual_income": 1500000
                  }
    Description: 
      1. Allows the users to register for a loan
      2. An async celery task is invoked to calculate the credit score
      3. Generates a unique user_uuid for the given user
    Response - {
                  "message": "user successfully registered",
                  "data": {
                      "user_uuid": "c9577b41-daaf-4276-9403-ba825fd1058c"
                  },
                  "success": "True"
                }

apply_loan - 
    
    URL - "http://127.0.0.1:8000/apply_loan/"
    Type - POST
    Request Body - {
                      "user_uuid":"c9577b41-daaf-4276-9403-ba825fd1058c",
                      "loan_type": "CAR",
                      "loan_amount":600000,
                      "interest_rate":15,
                      "term_period":10,
                      "disbursement_date":"2023-07-19"
                    }
    Description :
      1. Allows the user to apply for loans
      2. Generated a unique loan_id against the applied loan
      3. Generates EMI details such as emi_due, installment_date etc.

    Response - {
                "message": "loan applied successfuly",
                "data": {
                    "EMI_details": [
                        {
                            "amount_due": 64201.0,
                            "amount_paid": 0.0,
                            "installment_date": "2023-08-01 00:00:00+00:00"
                        },
                        {
                            "amount_due": 64201.0,
                            "amount_paid": 0.0,
                            "installment_date": "2023-09-01 00:00:00+00:00"
                        },
                        {
                            "amount_due": 64201.0,
                            "amount_paid": 0.0,
                            "installment_date": "2023-10-01 00:00:00+00:00"
                        },
                    "loan_id": "398ed9c2-287d-4bd7-b753-f26526d30ed9"
                },
                "success": "True"
                }

make_payment - 

    URL - "http://127.0.0.1:8000/make_payment/"
    Type - POST
    Request Body - {
                      "loan_id": "398ed9c2-287d-4bd7-b753-f26526d30ed9",
                      "amount": 100000
                    }
          
    Description :
      1. Allows the users to make payment for the due EMIs
      2. Recalculates the EMIs if the amount paid by the user is more than the EMI due for that given month
      
    Response - {
                "message": "EMI paid successfully for this month", 
                "data": {
                          "emi_due": 64487.0, "emi_paid": 100000, 
                          "installment_paid": "2023-11-01 00:00:00+00:00"
                        }, 
                "success": "True"
                }

get_statement - 

    URL - "http://127.0.0.1:8000/get_statement/?loan_id=398ed9c2-287d-4bd7-b753-f26526d30ed9"
    Type - GET
    Request Params - {
                        "loan_id":"398ed9c2-287d-4bd7-b753-f26526d30ed9"
                      }
                      
    Description : 
      1. Fetches the information of past transactions and upcoming transactions for the given loan id
      
    Response - {
                  "message": "success",
                  "data": {
                            "upcoming_transactions": [
                                {  
                                "amount_due": 51522,
                                "installment_date": "2023-09-01 00:00:00+00:00"
                                },
                                {
                                  "amount_due": 51522,
                                  "installment_date": "2023-09-01 00:00:00+00:00"
                                },
                              ],
                            "past_transactions": [
                                {
                                  "amount_paid": 64487,
                                  "installment_date": "2023-08-01 00:00:00+00:00"
                                },
                              ]
                            },
                  "success": "True"
                }
              
   
