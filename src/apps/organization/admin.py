from django.contrib import admin
from .models import Organization, Department, CostCenter, FiscalPeriod

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'organization')
    list_filter = ('organization',)
    search_fields = ('name', 'code')

@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'manager')
    list_filter = ('department',)
    search_fields = ('name', 'code')

@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'period_number', 'organization', 'start_date', 'end_date', 'is_closed')
    list_filter = ('organization', 'year', 'is_closed')
