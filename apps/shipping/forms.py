# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytz
import datetime
from django import forms
from django.conf import settings
from shipping.models import Milestone, AppVersion


class ModelInstanceField(forms.fields.Field):

    def __init__(self, model, key='pk', *args, **kwargs):
        self.model = model
        self.key = key
        self._instance = None
        super(ModelInstanceField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        "return the model instance if a value is supplied"
        if value:
            try:
                return self.model.objects.get(**{self.key: value})
            except self.model.DoesNotExist:
                raise forms.ValidationError(self.model._meta.verbose_name)


class SignoffFilterForm(forms.Form):
    ms = ModelInstanceField(Milestone, key='code', required=False)
    av = ModelInstanceField(AppVersion, key='code', required=False)
    up_until = forms.fields.DateTimeField(required=False)

    def clean_up_until(self):
        # the date is inputted as assumed, UTC datetime
        # but our data is stored with a local time, so we adjust it
        value = self.cleaned_data['up_until']
        if value:
            # convert it to a timezone aware datetime
            value = value.replace(tzinfo=pytz.UTC)
            local = pytz.timezone(settings.TIME_ZONE)
            # convert it into that timezone
            value = value.astimezone(local)
            # make it a naive datetime again
            value = value.replace(tzinfo=None)
        return value
