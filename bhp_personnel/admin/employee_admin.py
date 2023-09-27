import csv
from datetime import datetime

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import reverse, path
from edc_model_admin import StackedInlineMixin, ModelAdminFormAutoNumberMixin
from edc_model_admin.model_admin_audit_fields_mixin import audit_fieldset_tuple

from ..admin_site import bhp_personnel_admin
from ..forms import EmployeeForm, SupervisorForm, CSVUploadForm
from ..models import Employee, Supervisor, Department, Pi, Licence
from .modeladmin_mixins import ModelAdminMixin


class LicenceInline(StackedInlineMixin, ModelAdminFormAutoNumberMixin,
                                  admin.StackedInline):
    model = Licence
    extra = 0

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'employee',
                'number',
                'issued_by',
                'issue_date',
                'expiration_date',
            )
        }),
        audit_fieldset_tuple
    )



@admin.register(Supervisor, site=bhp_personnel_admin)
class SupervisorAdmin(ModelAdminMixin, admin.ModelAdmin):
    form = SupervisorForm

    fieldsets = (
        (None, {
            'fields': (
                'first_name',
                'last_name',
                'cell',
                'email',
            )}),
        audit_fieldset_tuple)

    search_fields = ['first_name', 'last_name', 'email',
                     'cell']


@admin.register(Employee, site=bhp_personnel_admin)
class EmployeeAdmin(ModelAdminMixin, admin.ModelAdmin):
    form = EmployeeForm
    inlines = [LicenceInline]

    fieldsets = (
        (None, {
            'fields': (
                'identifier',
                'first_name',
                'middle_name',
                'last_name',
                'gender',
                'title_salutation',
                'date_of_birth',
                'highest_qualification',
                'nationality',
                'identity',
                'identity_type',
                'country',
                'postal_address',
                'physical_address',
                'department',
                'supervisor',
                'studies',
                'cell',
                'next_of_kin_contact',
                'email',
                'job_title',
                'hired_date',
                'employee_code',
            )}),
        audit_fieldset_tuple)

    radio_fields = {
        'gender': admin.VERTICAL,
        'title_salutation': admin.VERTICAL,
        'highest_qualification': admin.VERTICAL,
        'nationality': admin.VERTICAL,
        'identity_type': admin.VERTICAL
    }

    search_fields = ['first_name', 'last_name', 'email', 'job_title',
                     'employee_code', 'identifier', 'cell']

    autocomplete_fields = ['supervisor', 'department', ]

    filter_horizontal = ('studies',)

    list_filter = ('department__dept_name', 'supervisor__first_name', 'job_title',)

    list_display = ('identifier', 'employee_code', 'first_name', 'last_name',
                    'department',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        fields = ['identity', 'cell', 'next_of_kin_contact']
        for field in fields:
            form.base_fields[field].help_text = ""
        return form

    def has_change_permission(self, request, obj=None):
        if 'HR' in request.user.groups.values_list('name', flat=True):
            return True
        return False

    def has_add_permission(self, request):
        if 'HR' in request.user.groups.values_list('name', flat=True):
            return True
        return False

    def get_urls(self):
        urls = super().get_urls()
        new_url = [
            path('import-employee/', self.import_employee),
        ]
        return new_url + urls

    def import_employee(self, request, *args, **kwargs):
        if not self.has_add_permission(request):
            self.message_user(request, "You do not have permission to perform this action."
                                       " Please contact an administrator for assistance.")
            return redirect('..')
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            decoded_file = request.FILES['csv_file'].read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            for row in reader:
                supervisor, _ = Supervisor.objects.get_or_create(
                    first_name=row.get('supervisor_first_name', ''),
                    last_name=row.get('supervisor_last_name', ''),
                    cell=row.get('supervisor_cell', ''),
                    email=row.get('supervisor_email', ''),
                )

                dept, _ = Department.objects.get_or_create(
                    hod=row.get('hod', ''),
                    dept_name=row.get('department_name', '')
                )

                employee, _ = Employee.objects.update_or_create(
                    email=row.get('email', ''),
                    employee_code=row.get('employee_code', ''),
                    cell=row.get('cell', ''),
                    identity=row.get('identity', ''),
                    next_of_kin_contact=row.get('next_of_kin_contact', ''),
                    defaults={
                        'first_name': row.get('first_name', ''),
                        'last_name': row.get('last_name', ''),
                        'gender': row.get('gender', ''),
                        'hired_date': datetime.strptime(row.get('hired_date', ''), '%Y-%m-%d').date(),
                        'identity_type': row.get('identity_type', ''),
                        'title_salutation': row.get('title_salutation', ''),
                        'highest_qualification': row.get('highest_qualification', ''),
                        'nationality': row.get('nationality', ''),
                        'country': row.get('country', ''),
                        'postal_address': row.get('postal_address', ''),
                        'physical_address': row.get('physical_address', ''),
                        'job_title': row.get('job_title', ''),
                        'date_of_birth': datetime.strptime(row.get('date_of_birth', ''), '%Y-%m-%d').date(),
                        'supervisor': supervisor,
                        'department': dept,
                    }
                )

                if row.get('job_title', '').lower() == 'principal investigator':
                    Pi.objects.get_or_create(
                        email=row.get('email', ''),
                        first_name=row.get('first_name', ''),
                        last_name=row.get('last_name', ''),
                        defaults={
                            'gender': row.get('gender', ''),
                            'hired_date': row.get('hired_date', ''),
                            'cell': row.get('cell', ''),
                        }
                    )
            self.message_user(request, "Employee's have been imported")
            return redirect('..')

        return render(request, 'cms_dashboard/employee/bulk_employee.html', {'form': form})
