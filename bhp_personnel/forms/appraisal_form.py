from django import forms
from django.core.exceptions import ValidationError
from django.apps import apps as django_apps
from edc_base.sites import SiteModelFormMixin
from edc_form_validators import FormValidator, FormValidatorMixin

from ..models import Appraisal, Employee


class AppraisalFormValidator(FormValidator):

    def clean(self):
        super().clean()
        supervisor_signature = self.cleaned_data.get('supervisor_signature')
        employee_signature = self.cleaned_data.get('employee_signature')

        emp_identifier = self.cleaned_data.get('emp_identifier')
        employee_cls = django_apps.get_model('bhp_personnel.employee')

        try:
            employee = employee_cls.objects.get(identifier=emp_identifier)
        except employee_cls.DoesNotExist:
            message = {'supervisor_signature': "Employee not found for the provided identifier."}
            self._errors.update(message)
            raise ValidationError(message)

        supervisor_full_name = f"{employee.supervisor.first_name} {employee.supervisor.last_name}"
        employee_full_name = f"{employee.first_name} {employee.last_name}"

        if supervisor_signature and supervisor_full_name != supervisor_signature:
            message = {'supervisor_signature': "The provided supervisor signature is incorrect."
                                               " Please enter the supervisor's full name (first name and last name)"
                                               " as the signature."}
            self._errors.update(message)
            raise ValidationError(message)

        if employee_signature and employee_signature != employee_full_name:
            message = {'employee_signature': "The provided employee signature is incorrect."
                                             " Please enter the employee's full name (first name and last name)"
                                             " as the signature."}
            self._errors.update(message)
            raise ValidationError(message)


class AppraisalForm(FormValidatorMixin, SiteModelFormMixin, forms.ModelForm):
    form_validator_cls = AppraisalFormValidator
    emp_identifier = forms.CharField(
        label='Employee ID',
        widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    class Meta:
        model = Appraisal
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        employee_id = self.initial['emp_identifier']
        employee = Employee.objects.filter(identifier=employee_id).first()

        is_supervisor = self.request.user.email == employee.supervisor.email
        is_employee = self.request.user.email == employee.email

        self.fields['contract'].disabled = True

        if not is_supervisor:
            self.fields['additional_comments'].disabled = True
            self.fields['supervisor_signature'].disabled = True
            self.fields['date_supervisor_signed'].disabled = True

        if not is_employee:
            self.fields['employee_signature'].disabled = True
            self.fields['staff_comments'].disabled = True
            self.fields['date_employee_signed'].disabled = True
