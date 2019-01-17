# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.apps import AppConfig
from .admin_site import admin_site
from django.contrib import admin as django_admin
from django.contrib.admin import sites as django_admin_sites


class ElmoConfig(AppConfig):
    """Monkey patches for elmo"""

    name = 'elmo'
    verbose_name = 'Elmo Site'

    def ready(self):
        # Monkeypatch session_csrf
        import session_csrf
        session_csrf.monkeypatch()
        # Set our admin site as admin.site
        django_admin.site = django_admin_sites.site = admin_site
        # Monkeypath hglib.client.pathto
        # Working around the lack of
        # https://bz.mercurial-scm.org/show_bug.cgi?id=4510
        from hglib.client import hgclient
        if not hasattr(hgclient, 'pathto'):
            import os
            from hglib.util import b

            def pathto(self, f, cwd='.'):
                """
                Return relative path to f. If cwd is given, use it as current
                working directory.
                The returned path uses os.sep as separator.

                f - file path with / as separator
                cwd - working directory with os.sep as separator
                """
                return b(
                    os.path.relpath(
                        os.path.join(
                            self.root().decode('latin-1'), *(f.split('/'))
                        ),
                        start=cwd
                    )
                )
            hgclient.pathto = pathto
