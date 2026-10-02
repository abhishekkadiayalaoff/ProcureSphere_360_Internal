from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from .models import Contract
from .permissions import CanViewContract, IsLegalManager
from .selectors import get_contracts_qs
from .serializers import (
    ContractSerializer,
    ContractVersionSerializer,
)
from .services import (
    approve_business_service,
    approve_legal_review_service,
    create_contract_service,
    create_contract_version_service,
    reject_legal_review_service,
    renew_contract_service,
    submit_for_legal_review_service,
    terminate_contract_service,
)


class ContractViewSet(viewsets.ModelViewSet):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, CanViewContract]

    def get_queryset(self):
        return get_contracts_qs(user=self.request.user)

    def perform_create(self, serializer):
        data = serializer.validated_data
        contract = create_contract_service(
            title=data["title"],
            vendor=data["vendor"],
            contract_value=data.get("contract_value", 0),
            start_date=data["start_date"],
            end_date=data["end_date"],
            contract_owner=self.request.user,
            renewal_notice_days=data.get("renewal_notice_days", 30),
            sourcing_event=data.get("sourcing_event"),
            po=data.get("po"),
        )
        serializer.instance = contract

    @action(detail=True, methods=["post"], url_path="submit-legal")
    def submit_legal(self, request, pk=None):
        contract = self.get_object()
        notes = request.data.get("notes", "")
        try:
            contract = submit_for_legal_review_service(contract=contract, user=request.user, notes=notes)
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_TRANSITION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="legal-approve", permission_classes=[IsAuthenticated, IsLegalManager])
    def legal_approve(self, request, pk=None):
        contract = self.get_object()
        notes = request.data.get("notes", "")
        try:
            contract = approve_legal_review_service(contract=contract, user=request.user, notes=notes)
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_TRANSITION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="legal-reject", permission_classes=[IsAuthenticated, IsLegalManager])
    def legal_reject(self, request, pk=None):
        contract = self.get_object()
        reason = request.data.get("reason", "")
        if not reason:
            return Response({"error": {"code": "MISSING_PARAM", "message": "Rejection reason required"}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            contract = reject_legal_review_service(contract=contract, user=request.user, reason=reason)
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_TRANSITION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="business-approve")
    def business_approve(self, request, pk=None):
        contract = self.get_object()
        notes = request.data.get("notes", "")
        try:
            contract = approve_business_service(contract=contract, user=request.user, notes=notes)
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_TRANSITION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="amend")
    def amend(self, request, pk=None):
        contract = self.get_object()
        summary = request.data.get("amendment_summary")
        value = request.data.get("contract_value")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not summary or not value or not start_date or not end_date:
            return Response({"error": {"code": "MISSING_PARAM", "message": "All amendment fields are required"}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            version = create_contract_version_service(
                contract=contract,
                user=request.user,
                amendment_summary=summary,
                contract_value=value,
                start_date=start_date,
                end_date=end_date,
            )
            return Response(ContractVersionSerializer(version).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_AMENDMENT", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="renew")
    def renew(self, request, pk=None):
        contract = self.get_object()
        new_end_date = request.data.get("new_end_date")
        new_value = request.data.get("new_value")
        notes = request.data.get("notes", "")
        if not new_end_date:
            return Response({"error": {"code": "MISSING_PARAM", "message": "new_end_date is required"}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            contract = renew_contract_service(
                contract=contract,
                user=request.user,
                new_end_date=new_end_date,
                new_value=new_value,
                notes=notes,
            )
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_RENEWAL", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="terminate")
    def terminate(self, request, pk=None):
        contract = self.get_object()
        reason = request.data.get("reason", "")
        if not reason:
            return Response({"error": {"code": "MISSING_PARAM", "message": "Termination reason is required"}}, status=status.HTTP_400_BAD_REQUEST)
        try:
            contract = terminate_contract_service(contract=contract, user=request.user, reason=reason)
            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": {"code": "INVALID_TERMINATION", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)
