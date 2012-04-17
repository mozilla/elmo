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

'''Mercurial repository hook to add changesets to the database on push.
'''

from datetime import datetime
import re
import os

from django.conf import settings

if not settings.configured:
    from l10n_site import local_settings
    d = dict(local_settings.__dict__)
    d['INSTALLED_APPS'] = ['life', 'pushes']
    settings.configure(**d)

from django.db import transaction
from life.models import Repository, Forest, Push
from pushes.utils import get_or_create_changeset


@transaction.commit_manually
def add_push(ui, repo, node, **kwargs):
    try:
        # all changesets from node to 'tip' inclusive are part of this push
        topdir = ui.config('pushes', 'topdir').split('/')
        baseurl = ui.config('pushes', 'baseurl')
        repo_name = repo.path.split('/')  # XXX os.sep?
        while topdir and topdir[0] == repo_name[0]:
            topdir.pop(0)
            repo_name.pop(0)
        if repo_name[-1] == '.hg':
            repo_name.pop()
        repo_name = '/'.join(filter(None, repo_name))
        url = baseurl + repo_name + '/'
        dbrepo, _created = Repository.objects.get_or_create(name=repo_name,
                                                            url=url)
        # figure out forest
        for _section, pattern in ui.configitems('pushes_forests'):
            m = re.match(pattern, repo_name)
            if m is None:
                continue
            f_url = baseurl + m.group() + '/'
            forest, _created = Forest.objects.get_or_create(name=m.group(),
                                                            url=f_url)
            dbrepo.forest = forest
            dbrepo.save()
            break
        changesets = []
        rev = repo.changectx(node).rev()
        tip = repo.changectx('tip').rev()
        for i in range(rev, tip + 1):
            ctx = repo.changectx(i)
            cs = get_or_create_changeset(dbrepo, repo, ctx.hex())
            transaction.commit()
            changesets.append(cs)
        p = Push.objects.create(repository=dbrepo,
                                push_id=dbrepo.last_known_push() + 1,
                                push_date=datetime.utcnow(),
                                user=os.environ['USER'])
        p.changesets = changesets
        p.save()
        transaction.commit()
        return 0
    except Exception, e:
        transaction.rollback()
        print e.message
        return 1
