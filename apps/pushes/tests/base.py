# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import os
import shutil
import tempfile
from django.conf import settings
from mercurial.ui import ui as hg_ui
from elmo.test import TestCase
from life.models import Repository
from ..utils import get_or_create_changeset


class mock_ui(hg_ui):
    def write(self, *msg, **opts):
        pass

    def warn(self, *msg, **opts):
        pass


class RepoTestBase(TestCase):

    def setUp(self):
        super(RepoTestBase, self).setUp()
        self._old_repository_base = getattr(settings, 'REPOSITORY_BASE', None)
        self._base = settings.REPOSITORY_BASE = tempfile.mkdtemp()

    def tearDown(self):
        super(RepoTestBase, self).tearDown()
        if os.path.isdir(self._base):
            shutil.rmtree(self._base)
        if self._old_repository_base is not None:
            settings.REPOSITORY_BASE = self._old_repository_base

    def dbrepo(self, name=None, changesets_from=None,
               urlpattern='http://localhost:8001/%s/'):
        if name is None:
            name = self.repo_name
        repo = Repository.objects.create(
          name=name,
          url=urlpattern % name
        )
        if changesets_from is None:
            return repo
        for rev in changesets_from:
            get_or_create_changeset(repo, changesets_from,
                                    changesets_from[rev].hex())
        return repo
