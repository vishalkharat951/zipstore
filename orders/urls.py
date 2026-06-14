from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order_list'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/status/', views.OrderStatusUpdateView.as_view(), name='order_status_update'),
    path('<int:pk>/cancel/', views.OrderCancelView.as_view(), name='order_cancel'),
    path('<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
]
