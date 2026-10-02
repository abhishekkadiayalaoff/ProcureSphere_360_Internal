from django.urls import path
from . import views

urlpatterns = [
    path("inbox/", views.inbox_view, name="approvals_inbox"),
]
