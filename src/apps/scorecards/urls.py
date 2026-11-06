from django.urls import path

from .views import (
    scorecard_calculate_view,
    scorecard_list_view,
    scorecard_vendor_detail_view,
)

urlpatterns = [
    path("scorecards/", scorecard_list_view, name="scorecard_list"),
    path("scorecards/calculate/", scorecard_calculate_view, name="scorecard_calculate"),
    path(
        "scorecards/vendor/<str:vendor_id>/",
        scorecard_vendor_detail_view,
        name="scorecard_vendor_detail",
    ),
]
