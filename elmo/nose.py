from __future__ import absolute_import
from django_nose.plugin import AlwaysOnPlugin

import os.path

apps_path = os.path.abspath(os.path.join(__file__, '..', '..', 'apps'))


class NoseAppsPlugin(AlwaysOnPlugin):
    name = 'elmo-apps'

    def wantDirectory(self, dirname):
        if dirname == apps_path:
            return True
        return
