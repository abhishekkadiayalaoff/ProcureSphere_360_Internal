from django.contrib import admin

from apps.contracts.models import Contract, ContractAlert, ContractMilestone, ContractVersion


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "contract_number",
        "title",
        "vendor",
        "contract_value",
        "status",
        "start_date",
        "end_date",
    )
    list_filter = ("status",)
    search_fields = ("contract_number", "title", "vendor__legal_name")


admin.site.register(ContractVersion)
admin.site.register(ContractMilestone)
admin.site.register(ContractAlert)
