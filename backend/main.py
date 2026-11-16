from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import accounts, auth, payment_methods, plans, registration, subscriptions, profiles

app = FastAPI(
    title="QuaseFlix API",
    version="1.0.0"
)

'''
Enable CORS (Cross-Origin Resource Sharing)
This acts as an official permission pass so the web browser allows the 
frontend (running on a different port) to send requests to this backend API
'''
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"], # Allows frontend apps from any website
    allow_credentials = True, # Allows the frontend to send sensitive items like login cookies
    allow_methods = ["*"], # Allows the frontend to use any HTTP method
    allow_headers = ["*"], # Allows the frontend to send standard data headers
)

# Include the accounts router
app.include_router(accounts.router)

# Include the authentication router (login)
app.include_router(auth.router)

# Include the payment methods router
app.include_router(payment_methods.router)

# Include the plans router
app.include_router(plans.router)

app.include_router(registration.router)

app.include_router(subscriptions.router)

app.include_router(profiles.router)
