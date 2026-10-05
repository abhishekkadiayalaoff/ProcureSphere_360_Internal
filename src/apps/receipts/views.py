from django.shortcuts import render
from apps.receipts.models import GoodsReceipt
from apps.orders.models import PurchaseOrder


def receipts_list_view(request):
    receipts = GoodsReceipt.objects.select_related("po", "received_by").order_by("-received_date")
    open_pos = PurchaseOrder.objects.filter(status__in=["ISSUED", "ACKNOWLEDGED", "PARTIAL_RECEIPT"])
    return render(request, "receipts/receipts_list.html", {
        "receipts": receipts,
        "open_pos": open_pos,
    })
