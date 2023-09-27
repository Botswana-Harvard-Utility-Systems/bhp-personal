from django import forms

from edc_base.sites import SiteModelFormMixin

from ..models import RenewalIntent, Contract, Employee


class RenewalIntentForm(SiteModelFormMixin, forms.ModelForm):
    contract = forms.ModelChoiceField(
        label='Contract',
        queryset=Contract.objects.none(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        contract_id = self.request.GET.get('contract')
        if contract_id:
            contract = Contract.objects.filter(id=contract_id).first()
            if contract:
                self.fields['contract'].queryset = Contract.objects.filter(id=contract.id)
                employee = Employee.objects.filter(identifier=contract.identifier).first()
                if employee:
                    is_employee = self.request.user.email == employee.email
                    is_supervisor = self.request.user.email == employee.supervisor.email
                    if not is_employee:
                        self.fields['intent'].disabled = True
                        self.fields['letter_upload'].disabled = True
                    elif not is_supervisor:
                        self.fields['comment'].disabled = True

    class Meta:
        model = RenewalIntent
        fields = '__all__'
