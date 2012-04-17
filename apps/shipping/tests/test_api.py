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
#    Peter Bengtsson <peterbe@mozilla.com>
#    Axel Hecht <l10n@mozilla.com>
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

from django.test import TestCase
from shipping.models import Signoff, Action
from shipping.api import signoff_actions, flag_lists
from nose.tools import eq_


class ApiActionTest(TestCase):
    fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    def test_count(self):
        """Test that we have the right amount of Signoffs and Actions"""
        eq_(Signoff.objects.count(), 5)
        eq_(Action.objects.count(), 8)

    def test_accepted(self):
        """Test for the german accepted signoff"""
        actions = signoff_actions(appversions={"code": "fx1.0"},
                                  locales={"code": "de"})
        actions = list(actions)
        eq_(len(actions), 1)
        so = Signoff.objects.get(action=actions[0][0])
        eq_(so.push.tip.shortrev, "l10n de 0002")
        eq_(so.locale.code, "de")
        eq_(so.action_set.count(), 2)

    def test_pending(self):
        """Test for the pending polish signoff"""
        actions = signoff_actions(appversions={"code": "fx1.0"},
                                  locales={"code": "pl"})
        actions = list(actions)
        eq_(len(actions), 1)
        so = Signoff.objects.get(action=actions[0][0])
        eq_(so.push.tip.shortrev, "l10n pl 0003")
        eq_(so.locale.code, "pl")
        eq_(so.action_set.count(), 1)

    def test_rejected(self):
        """Test for the rejected polish signoff"""
        actions = signoff_actions(appversions={"code": "fx1.0"},
                                  locales={"code": "fr"})
        actions = list(actions)
        eq_(len(actions), 1)
        eq_(actions[0][1], Action.REJECTED)
        so = Signoff.objects.get(action=actions[0][0])
        eq_(so.push.tip.shortrev, "l10n fr 0003")
        eq_(so.locale.code, "fr")
        eq_(so.action_set.count(), 2)

    def test_getlist(self):
        """Test that the list returns the right flags."""
        flags = flag_lists(appversions={"code": "fx1.0"})
        # note that the flags below are [1, 0] (and not [0, 1])
        # which means the ACCEPTED comes *before* PENDING
        eq_(flags, {("fx", "pl"): [Action.PENDING],
                     ("fx", "de"): [Action.ACCEPTED],
                     ("fx", "fr"): [Action.REJECTED],
                     ("fx", "da"): [Action.ACCEPTED, Action.PENDING]})
