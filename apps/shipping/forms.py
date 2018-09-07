# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
from shipping.models import AppVersion


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
    av = ModelInstanceField(AppVersion, key='code')
    up_until = forms.fields.DateTimeField(required=False)


class SignoffsPaginationForm(forms.Form):
    push_date = forms.DateTimeField(
        input_formats=forms.DateTimeField.input_formats + [
            '%Y-%m-%dT%H:%M:%S',  # isoformat
        ]
    )
