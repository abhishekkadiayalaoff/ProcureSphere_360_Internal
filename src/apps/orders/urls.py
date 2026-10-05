from django.urls import path
from . import views

urlpatterns = [
    path("purchase-orders/", views.list_view, name="orders_list"),
    path("purchase-orders/<uuid:pk>/", views.detail_view, name="order_detail"),
    path("orders/", views.list_view, name="orders_list_alias"),
    path("orders/<uuid:pk>/", views.detail_view, name="order_detail_alias"),
]

