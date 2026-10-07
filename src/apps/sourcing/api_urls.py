from rest_framework.routers import DefaultRouter

from .api_views import (
    BidEvaluationViewSet,
    ClarificationViewSet,
    SourcingEventViewSet,
    VendorBidViewSet,
)

router = DefaultRouter()
router.register(r"events", SourcingEventViewSet, basename="sourcing-event")
router.register(r"bids", VendorBidViewSet, basename="vendor-bid")
router.register(r"clarifications", ClarificationViewSet, basename="sourcing-clarification")
router.register(r"evaluations", BidEvaluationViewSet, basename="bid-evaluation")

urlpatterns = router.urls
