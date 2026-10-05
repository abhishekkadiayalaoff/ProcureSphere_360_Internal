from django.urls import path
from . import views

urlpatterns = [
    path("purchase-orders/", views.list_view, name="orders_list"),
    path("orders/", views.list_view, name="orders_list_alias"),
]

