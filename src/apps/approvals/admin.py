from django.contrib import admin
from .models import ApprovalPolicy, ApprovalStep, ApprovalAction

@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'department', 'min_amount', 'max_amount', 'is_active')
    list_filter = ('module', 'is_active')
    search_fields = ('name',)

@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ('policy', 'step_number', 'approver_role', 'specific_approver')
    list_filter = ('approver_role',)

@admin.register(ApprovalAction)
class ApprovalActionAdmin(admin.ModelAdmin):
    list_display = ('target_model_name', 'target_object_id', 'actor', 'action', 'created_at')
    list_filter = ('action', 'target_model_name')
