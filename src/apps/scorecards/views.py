from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import VendorScorecard


@login_required
def scorecard_list_view(request):
    """
    Supplier Performance Scorecard leaderboard view.
    """
    scorecards = VendorScorecard.objects.select_related("vendor").order_by("-overall_score")

    return render(
        request,
        "scorecards/scorecard_list.html",
        {
            "scorecards": scorecards,
        },
    )
