from django.urls import path
from .views import receipts_list_view

urlpatterns = [
    path("receipts/", receipts_list_view, name="receipts_list"),
]
