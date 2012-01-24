# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Command to update a tree of local repositories according to the status
of an upstream database.
'''

from optparse import make_option

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--rebase', action='store_true',
                    help='Use --rebase for hg pull'),
        make_option('-u', '--update', action='store_true',
                    help='Use -u for hg pull'),
        make_option('-a', '--all', action='store_true',
                    help='Refresh all repositories'),
        )
    help = 'Update set of local clones'

    def handle(self, *args, **options):
        rebase = options.get('rebase', False)
        update = options.get('update', False)
        all = options.get('all', False)
        if rebase:
            pull_args = ['--rebase']
        elif update:
            pull_args = ['-u']
        else:
            pull_args = []
        from life.models import Repository, Changeset
        from pushes.management import hgcompat
        import os.path
        from django.conf import settings

        def resolve(path):
            return os.path.join(settings.REPOSITORY_BASE, *path.split('/'))

        # check for last push helper file
        if not all and os.path.isfile(resolve('.latest_cs')):
            latest_cs = int(open(resolve('.latest_cs')).read())
            repos = (Repository.objects
                     .filter(changesets__id__gt=latest_cs)
                     .distinct())
        else:
            repos = Repository.objects.all()
        latest_cs = Changeset.objects.order_by('-pk')[0].id

        for name, url in repos.values_list('name', 'url'):
            repopath = str(resolve(name))
            if not os.path.isdir(os.path.join(repopath, '.hg')):
                # new repo, need to clone
                if os.path.isdir(repopath):
                    print ("\n\nCannot clone %s, "
                           "existing directory in the way\n\n") % name
                    continue
                _parent = os.path.dirname(repopath)
                if not os.path.isdir(_parent):
                    try:
                        os.makedirs(_parent)
                    except Exception, e:
                        print ("\n\nFailed to prepare for clone, %s\n\n"
                               % str(e))
                        continue
                hgcompat.dispatch(['clone', str(url), repopath])
            else:
                hgcompat.dispatch(['pull', '-R', repopath] + pull_args)

        open(resolve('.latest_cs'), 'w').write('%i\n' % latest_cs)
