# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
from django.core.management.base import BaseCommand
from webby.models import Project
from webby.utils import update_verbatim_all, update_svn_all


class Command(BaseCommand):
    help = 'Updates stats on all webby projects'

    def handle(self, *args, **options):
        projects = Project.objects.all()
        for project in projects:
            print('Updating project [%s]: \n' % project.slug)
            try:
                print('  Verbatim:')
                update_verbatim_all(project)
                print(' OK\n')
            except:
                print(' Failed\n')
            try:
                print('  SVN: ')
                update_svn_all(project)
                print(' OK\n')
            except:
                print(' Failed\n')

        print('Webby updated\n')
