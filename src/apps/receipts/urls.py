from django.urls import path

from .views import (
    receipt_create_view,
    receipt_detail_view,
    receipt_inspect_view,
    receipt_stock_handoff_view,
    receipts_list_view,
)

urlpatterns = [
    path("receipts/", receipts_list_view, name="receipts_list"),
    path("receipts/create/<uuid:po_id>/", receipt_create_view, name="receipt_create"),
    path("create/<uuid:po_id>/", receipt_create_view, name="receipt_create_alt"),
    path("receipts/<uuid:grn_id>/", receipt_detail_view, name="receipt_detail"),
    path("receipts/<uuid:grn_id>/inspect/", receipt_inspect_view, name="receipt_inspect"),
    path(
        "receipts/<uuid:grn_id>/handoff/", receipt_stock_handoff_view, name="receipt_stock_handoff"
    ),
]
