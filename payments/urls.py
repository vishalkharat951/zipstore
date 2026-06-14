from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/<int:order_id>/', views.InitiatePaymentView.as_view(), name='initiate_payment'),
    path('callback/', views.PaymentCallbackView.as_view(), name='payment_callback'),
    path('redirect/', views.PaymentRedirectView.as_view(), name='payment_redirect'),
    path('success/<int:order_id>/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('failure/<int:order_id>/', views.PaymentFailureView.as_view(), name='payment_failure'),
    path('upi/<int:order_id>/', views.UPIPaymentView.as_view(), name='upi_payment'),
]
