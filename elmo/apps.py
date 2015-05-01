# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from django.apps import AppConfig


class ElmoConfig(AppConfig):
    """Monkey patches for elmo"""
    
    name = 'elmo'
    verbose_name = 'Elmo Site'
    
    def ready(self):
        ## Monkeypatch session_csrf
        import session_csrf
        session_csrf.monkeypatch()
        from funfactory import admin
        admin.monkeypatch()
