from django.contrib import admin
from apps.contracts.models import Contract, ContractAlert, ContractMilestone, ContractVersion
from apps.core.admin_site import RoleBasedModelAdmin, register_model


class ContractAdmin(RoleBasedModelAdmin):
    list_display = ("contract_number", "title", "vendor", "contract_value", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("contract_number", "title", "vendor__legal_name")


register_model(Contract, ContractAdmin)
register_model(ContractVersion)
register_model(ContractMilestone)
register_model(ContractAlert)
