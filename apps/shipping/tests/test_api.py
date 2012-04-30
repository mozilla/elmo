# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
