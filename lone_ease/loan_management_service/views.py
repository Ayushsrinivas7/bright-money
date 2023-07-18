from django.shortcuts import render

app_name = "loan_management_service"
# Create your views here.

def register_user(request):

    if request.method == "POST":

        payload = request.POST
        aadhar_id = payload.get("aadhar_id")
        name = payload.get("name")
        email_id = payload.get("email_id")
        annual_income = payload.get("annual_income")

        # calculating credit score which will be invoked in a celery task further


