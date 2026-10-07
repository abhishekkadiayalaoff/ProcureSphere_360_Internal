from rest_framework import permissions, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter

from apps.audit.permissions import AuditorReadOnlyPermission

from .models import PRAttachment, PRLine, PurchaseRequisition


class PRLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PRLine
        fields = "__all__"


class PRAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PRAttachment
        fields = "__all__"


class PurchaseRequisitionSerializer(serializers.ModelSerializer):
    lines = PRLineSerializer(many=True, read_only=True)
    attachments = PRAttachmentSerializer(many=True, read_only=True)
    requester_email = serializers.CharField(source="requester.email", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = PurchaseRequisition
        fields = "__all__"


class CanCreateRequisitionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            user = request.user
            if not user or not user.is_authenticated:
                return False
            if user.is_superuser:
                return True
            role_code = getattr(user, "role_code", None) or (
                user.role.code if hasattr(user, "role") and user.role else None
            )
            return role_code in ["REQUESTER", "SUPER_ADMIN"]
        return True


class PurchaseRequisitionViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseRequisition.objects.select_related("requester", "department", "cost_center")
        .prefetch_related("lines", "attachments")
        .all()
    )
    serializer_class = PurchaseRequisitionSerializer
    permission_classes = [
        IsAuthenticated,
        AuditorReadOnlyPermission,
        CanCreateRequisitionPermission,
    ]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role_code in [
            "SUPER_ADMIN",
            "PROC_EXEC",
            "PROC_MGR",
            "AUDITOR",
        ]:
            return self.queryset
        # Requester / Approver scoped by department
        if user.department_id:
            return self.queryset.filter(department_id=user.department_id)
        return self.queryset.filter(requester=user)

    def perform_create(self, serializer):
        user = self.request.user
        role_code = getattr(user, "role_code", None) or (
            user.role.code if hasattr(user, "role") and user.role else None
        )
        if not user.is_superuser and role_code not in ["REQUESTER", "SUPER_ADMIN"]:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only users with the Requester role can raise Purchase Requisitions."
            )
        serializer.save(requester=user)


router = DefaultRouter()
router.register(r"", PurchaseRequisitionViewSet, basename="requisition")

urlpatterns = router.urls
