from django.contrib import admin
from edc_model_admin.model_admin_audit_fields_mixin import (
    audit_fieldset_tuple)
from .modeladmin_mixins import ModelAdminMixin
from ..admin_site import bhp_personnel_admin
from ..forms import AppraisalForm, PerformanceReviewForm
from ..models import Appraisal, PerformanceReview
from edc_model_admin import TabularInlineMixin, ModelAdminFormAutoNumberMixin


class PerformanceReviewAdmin(TabularInlineMixin, ModelAdminFormAutoNumberMixin,
                             admin.TabularInline):
    model = PerformanceReview
    form = PerformanceReviewForm

    fieldsets = (
        (None, {
            'fields': (
                'kpa_title',
                'kpa_description',
                'review_score')}),
    )


@admin.register(Appraisal, site=bhp_personnel_admin)
class AppraisalAdmin(ModelAdminMixin, admin.ModelAdmin):
    form = AppraisalForm
    inlines = [PerformanceReviewAdmin]

    fieldsets = (
        (None, {
            'fields': (
                'emp_identifier',
                'contract',
                'assessment_type',
                'supervisor_signature',
                'date_supervisor_signed',
                'employee_signature',
                'date_employee_signed',
                'additional_comments',
                'staff_comments'
            )}),
        audit_fieldset_tuple)

    radio_fields = {
        'assessment_type': admin.VERTICAL, }

