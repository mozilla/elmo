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
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Axel Hecht <l10n@mozilla.com>
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

'''Command to fix any of the repositories in the database miss changeset mappings.
'''

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from optparse import make_option
import sys

from django.core.management.base import CommandError
from ..base import RepositoryCommand
# XXX Achtung, Baby, django internals used here
from django.db.models.sql import InsertQuery
from django.db import router, transaction, connections

from life.models import Changeset

class Command(RepositoryCommand):
    option_list = RepositoryCommand.option_list + (
        make_option('--chunk-size', type = 'int', default=50,
                    help = 'Specify the chunk size to use for changeset queries [default=50]'),
        )
    help = 'Find repositories with missing changeset entries in the db.'

    def handleOptions(self, **kwargs):
        self.chunksize = kwargs.get('chunk_size', self.chunksize)

    def handleRepoWithCounts(self, dbrepo, hgrepo, dbcount, hgcount):
        """Just check if changesets counts in db and hg are the same
        """
        if dbcount >= hgcount:
            # nothing to be done
            self.verbose("%s\tin good shape" % self.dbrepo)
            return
        missing = hgcount - dbcount
        cnt = 0
        through = dbrepo.changesets.through
        using = router.db_for_write(dbrepo.__class__, instance=dbrepo)
        connection = connections[using]
        ins = InsertQuery(through)
        ins.insert_values([(through.repository.field, None), (through.changeset.field, None)])
        comp = ins.get_compiler(using)
        comp.return_id = False
        sqlinsert, _params = comp.as_sql()
        
        self.verbose("%s\t%d missing" % (dbrepo.name, missing))
        for revisions in self.chunk(self.nodes(hgrepo)):
            self.progress()
            with transaction.commit_on_success(using=using):
                cs = Changeset.objects.filter(revision__in=revisions)
                cs = cs.exclude(repositories=dbrepo)
                csids = list(cs.values_list('id', flat=True))
                if not csids:
                    continue
                vals = [(dbrepo.id, csid) for csid in csids]
                connection.cursor().executemany(sqlinsert, vals)
                transaction.set_dirty(using)
        self.normal("%s\tadded %d changesets" % (dbrepo.name, cnt))
        return

    chunksize=50
    def chunk(self, _iter):
        i = 0
        while True:
            chunk = []
            for o in _iter:
                chunk.append(o)
                if self.chunksize is not None and len(chunk) >= self.chunksize:
                    break
            if chunk:
                yield chunk
            else:
                break

    def nodes(self, hgrepo):
        for i in hgrepo:
            yield hgrepo[i].hex()
