from django import forms
from apps.accounts.models import User, Role
from apps.organization.models import Organization, Department

class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone_number', 'role', 'department', 'is_active']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class OrganizationAdminForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['code', 'name', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

from apps.budgets.models import Budget
from apps.approvals.models import ApprovalPolicy

class BudgetAdminForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['cost_center', 'fiscal_period', 'allocated_amount', 'allow_overspend']
        widgets = {
            'cost_center': forms.Select(attrs={'class': 'form-select'}),
            'fiscal_period': forms.Select(attrs={'class': 'form-select'}),
            'allocated_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'allow_overspend': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class PolicyAdminForm(forms.ModelForm):
    class Meta:
        model = ApprovalPolicy
        fields = ['name', 'module', 'department', 'min_amount', 'max_amount', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'module': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'min_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
