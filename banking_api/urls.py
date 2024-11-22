from django.urls import path
from .views import RegisterView, AdminOnlyView, AccountInfoView, TransactionView, TransactionHistoryView, BalanceCheckView, VerifyOTPView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('admin-only-endpoint/', AdminOnlyView.as_view(), name='admin_only_endpoint'),  
    path('account-info/', AccountInfoView.as_view(), name='account_info'),
    path('transactions/', TransactionView.as_view(), name='transactions'),
    path('transactions/history/', TransactionHistoryView.as_view(), name='transaction-history'),
    path('transactions/<int:transaction_id>/', TransactionView.as_view(), name='transaction_detail'),
    path('balance/', BalanceCheckView.as_view(), name='balance_check'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
]
