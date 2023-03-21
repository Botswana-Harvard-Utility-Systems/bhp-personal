from django.db import models

from edc_base.model_mixins import BaseUuidModel
from edc_base.sites.site_model_mixin import SiteModelMixin
from edc_constants.choices import YES_NO

from .contract import Contract


class RenewalIntent(BaseUuidModel, SiteModelMixin):
    contract = models.OneToOneField(
        Contract,
        on_delete=models.CASCADE
    )

    intent = models.CharField(
        verbose_name="Do you intend on renewing contract",
        max_length=10,
        choices=YES_NO,
        help_text='Yes or NO'
    )

    comment = models.TextField(
        verbose_name="Supervisor comment",
        blank=True,
        null=True
    )

    class Meta:
        app_label = 'bhp_personnel'
        verbose_name = 'Intent To Renew'
        verbose_name_plural = 'Intent To Renew'
