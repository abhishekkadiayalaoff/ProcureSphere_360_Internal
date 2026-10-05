from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "target_model", "target_object_id", "ip_address")
    list_filter = ("action", "target_model", "timestamp")
    search_fields = ("actor__email", "target_model", "target_object_id")
    readonly_fields = (
        "timestamp",
        "actor",
        "action",
        "target_model",
        "target_object_id",
        "previous_state",
        "new_state",
        "ip_address",
        "user_agent",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
