# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django import forms
import django.contrib.auth.forms


class AuthenticationForm(django.contrib.auth.forms.AuthenticationForm):
    """override the authentication form because we use the email address as the
    key to authentication."""
    username = forms.CharField(label="Username", max_length=75)

    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['placeholder'] = 'Email'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'
