from django import forms

from .models import Vendor, VendorCategory, VendorRiskRecord


class VendorRegistrationForm(forms.Form):
    legal_name = forms.CharField(max_length=255)
    trade_name = forms.CharField(max_length=255, required=False)
    tax_identification_number = forms.CharField(max_length=100)
    registration_number = forms.CharField(max_length=100, required=False)
    category = forms.ModelChoiceField(queryset=VendorCategory.objects.order_by("name"))
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
    bank_name = forms.CharField(max_length=150, required=False)
    bank_account_number = forms.CharField(max_length=100, required=False)
    bank_routing_code = forms.CharField(max_length=100, required=False)

    def clean_tax_identification_number(self):
        tin = self.cleaned_data["tax_identification_number"].strip()
        if Vendor.objects.filter(tax_identification_number=tin).exists():
            raise forms.ValidationError("A vendor with this tax ID already exists.")
        return tin


class RiskAssessmentForm(forms.Form):
    risk_level = forms.ChoiceField(
        choices=VendorRiskRecord.RISK_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    risk_flags = forms.MultipleChoiceField(
        choices=VendorRiskRecord.RISK_FLAG_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control form-control-sm"})
    )


class GovernanceStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Vendor.STATUS_CHOICES)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
