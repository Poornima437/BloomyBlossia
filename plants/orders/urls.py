from django.urls import path
from . import views

app_name = "orders" 

# Checkout & Orders
urlpatterns = [
   
    path("checkout/", views.checkout_view, name="checkout"),
    path("place-order/", views.place_order_view, name="place_order"),
    path("order-success/<str:order_id>/", views.order_success, name="order_success"),
    # path('track/<str:order_id>/', views.track_order, name='track_order'),
    path("orders/", views.orders_list, name="orders_list"),
    path("<str:order_id>/", views.order_detail, name="order_detail"),
    path("<str:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("<str:order_id>/return/", views.return_order, name="return_order"),
    path("<str:order_id>/download-invoice/", views.download_invoice, name="download_invoice"),
    path("order/<str:order_id>/return/", views.submit_return_request, name="submit_return_request"),

    path('order/item/<int:item_id>/cancel/', views.cancel_order_item, name='cancel_order_item'),
    path('order/item/<int:item_id>/return/', views.return_order_item, name='return_order_item'),
]







