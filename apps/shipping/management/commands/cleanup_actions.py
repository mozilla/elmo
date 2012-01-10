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

'''Update all local clones to the revisions that are shipped with a milestone.
'''

from collections import defaultdict
from optparse import make_option

from django.core.management.base import BaseCommand
from shipping.models import Action


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest='quiet', action='store_true',
                    help='Run quietly'),
        make_option('-n', '--dry-run', dest='dry', action='store_true',
                    help='Do not actually remove actions'),
        )
    help = 'Clean up actions that have been excessively cloned'

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        dry = options.get('dry', False)
        aq = Action.objects.order_by('-when')
        if not quiet:
            print 'Total action count at start: ', aq.count()
        cut = aq.values_list('when', flat=True)[0]
        while cut is not None:
            try:
                next_cut = (aq.filter(when__lte=cut)
                            .values_list('when', flat=True)[100])
            except IndexError:
                next_cut = None
            slice = aq.filter(when__lte=cut)
            if next_cut is not None:
                slice = slice.filter(when__gt=next_cut)
            c = defaultdict(list)
            for a in slice:
                c[(a.when, a.author_id, a.signoff_id, a.flag)].append(a.id)
            dupes = dict(filter(lambda t: len(t[1]) > 1, c.iteritems()))
            obsolete = []
            for a_ids in dupes.itervalues():
                obsolete += a_ids[:-1]
            if not quiet and obsolete:
                print 'Deleting %d actions' % len(obsolete)
            if not dry and obsolete:
                Action.objects.filter(id__in=obsolete).delete()
            cut = next_cut
        if not quiet:
            print 'Total action count now: ', aq.count()
