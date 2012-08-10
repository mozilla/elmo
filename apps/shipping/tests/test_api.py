# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.test import TestCase
from django.contrib.auth.models import User
from life.models import Tree, Forest, Locale
from shipping.models import (Signoff, Action, Application, AppVersion,
                             AppVersionTreeThrough)
from shipping.api import (_actions4appversion, actions4appversions,
                          flags4appversions)
from nose.tools import eq_, ok_
from datetime import datetime, timedelta


class ApiActionTest(TestCase):
    fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    def test_count(self):
        """Test that we have the right amount of Signoffs and Actions"""
        eq_(Signoff.objects.count(), 5)
        eq_(Action.objects.count(), 8)

    def test_getflags(self):
        """Test that the list returns the right flags."""
        flags = flags4appversions(appversions={"code": "fx1.0"})
        av = AppVersion.objects.get(code="fx1.0")
        eq_(flags, {av: {
            "pl": ["fx1.0", {Action.PENDING: 2}],
            "de": ["fx1.0", {Action.ACCEPTED: 3}],
            "fr": ["fx1.0", {Action.REJECTED: 5}],
            "da": ["fx1.0", {Action.ACCEPTED: 8,
                             Action.PENDING: 7}]
        }})


class ApiMigrationTest(TestCase):
    """Testcases for multiple appversions and signoff fallbacks."""
    # fixture sets up empty repos and forest for da, de, fr, pl
    fixtures = ["test_empty_repos.json"]
    pre_date = datetime(2010, 5, 15)
    migration = datetime(2010, 6, 1)
    post_date = datetime(2010, 6, 15)
    day = timedelta(days=1)

    def setUp(self):
        super(ApiMigrationTest, self).setUp()
        self.forest = Forest.objects.get(name='l10n')
        self.tree = Tree.objects.create(code='fx', l10n=self.forest)
        self.app = Application.objects.create(name="firefox", code="fx")
        self.old_av = self.app.appversion_set.create(code='fx1.0',
                                                     version='1.0',
                                                     accepts_signoffs=False)
        self.new_av = self.app.appversion_set.create(code='fx1.1',
                                                     version='1.1',
                                                     accepts_signoffs=True,
                                                     fallback=self.old_av)
        (AppVersionTreeThrough.objects
         .create(appversion=self.old_av,
                 tree=self.tree,
                 start=None,
                 end=self.migration))
        (AppVersionTreeThrough.objects
         .create(appversion=self.new_av,
                 tree=self.tree,
                 start=self.migration,
                 end=None))
        self.csnumber = 1
        self.localizer = User.objects.create(username='localizer')
        self.driver = User.objects.create(username='driver')
        self.actions = []

    def _setup(self, locale, before, after):
        """Create signoffs before and after migration, in the given state"""
        repo = self.forest.repositories.get(locale=locale)

        def _create(self, repo, av, d, state):
            # helper, create Changeset, Push, Signoff and Actions
            # for the given date
            if state is None:
                return
            cs = repo.changesets.create(revision='%012d' % self.csnumber)
            self.csnumber += 1
            p = repo.push_set.create(user='jane_doe',
                                     push_date=d)
            p.changesets = [cs]
            p.save()
            so = (Signoff.objects
                  .create(push=p,
                          appversion=av,
                          author=self.localizer,
                          when=d,
                          locale=repo.locale))
            a = so.action_set.create(flag=Action.PENDING,
                                     author=self.localizer,
                                     when=d)
            self.actions.append(a)
            if state != Action.PENDING:
                a = so.action_set.create(flag=state,
                                         author=self.driver,
                                         when=d + self.day)
                self.actions.append(a)
        _create(self, repo, self.old_av, self.pre_date, before)
        _create(self, repo, self.new_av, self.post_date, after)
        return repo

    def testEmpty(self):
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, None, None)
        eq_(repo.changesets.count(), 1)
        eq_(_actions4appversion(self.old_av, set([locale.id]), 100),
            ({}, set([locale.id])))
        eq_(_actions4appversion(self.new_av, set([locale.id]), 100),
            ({}, set([locale.id])))
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {})
        eq_(flagdata[self.old_av], flagdata[self.new_av])

    def testOneOld(self):
        """One locale signed off and accepted on old appversion,
        nothing new on new, thus falling back to the old one.
        """
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, Action.ACCEPTED, None)
        eq_(repo.changesets.count(), 2)
        flaglocs4av, not_found = _actions4appversion(self.old_av,
                                                     set([locale.id]),
                                                     100)
        eq_(not_found, set())
        eq_(flaglocs4av.keys(), [locale.id])
        flag, action_id = flaglocs4av[locale.id].items()[0]
        eq_(flag, Action.ACCEPTED)
        eq_(Signoff.objects.get(action=action_id).locale_id, locale.id)
        eq_(_actions4appversion(self.new_av, set([locale.id]), 100),
            ({}, set([locale.id])))
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {'da':
            ['fx1.0', {Action.ACCEPTED: self.actions[1].id}]
            })
        eq_(flagdata[self.old_av], flagdata[self.new_av])

    def testOneOldOneNewByActionDate(self):
        """One locale signed off and accepted on old appversion,
        nothing new on new, thus falling back to the old one.
        """
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, Action.ACCEPTED, Action.ACCEPTED)
        eq_(repo.changesets.count(), 3)
        flaglocs4av, __ = _actions4appversion(
            self.old_av,
            set([locale.id]),
            100,
        )
        actions = flaglocs4av[locale.id]
        action = Action.objects.get(pk=actions.values()[0])
        eq_(action.flag, Action.ACCEPTED)

        flaglocs4av, __ = _actions4appversion(
            self.old_av,
            set([locale.id]),
            100,
            up_until=self.pre_date
        )
        actions = flaglocs4av[locale.id]
        action = Action.objects.get(pk=actions.values()[0])
        eq_(action.flag, Action.PENDING)

        flaglocs4av, __ = _actions4appversion(
            self.old_av,
            set([locale.id]),
            100,
            up_until=self.post_date
        )
        actions = flaglocs4av[locale.id]
        action = Action.objects.get(pk=actions.values()[0])
        eq_(action.flag, Action.ACCEPTED)

    def testOneNew(self):
        """One accepted signoff on the new appversion, none on the old.
        Old appversion comes back empty.
        """
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, None, Action.ACCEPTED)
        eq_(repo.changesets.count(), 2)
        eq_(_actions4appversion(self.old_av, set([locale.id]), 100),
            ({}, set([locale.id])))
        a4av, not_found = _actions4appversion(self.new_av,
                                              set([locale.id]), 100)
        eq_(not_found, set())
        eq_(a4av.keys(), [locale.id])
        flag, action_id = a4av[locale.id].items()[0]
        eq_(flag, Action.ACCEPTED)
        eq_(Signoff.objects.get(action=action_id).locale_id, locale.id)
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {'da':
            ['fx1.1', {Action.ACCEPTED: self.actions[1].id}]})
        eq_(flagdata[self.old_av], {})

    def testOneOldAndNew(self):
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, Action.ACCEPTED, Action.ACCEPTED)
        eq_(repo.changesets.count(), 3)
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {'da':
            ['fx1.1', {Action.ACCEPTED: self.actions[3].id}]
            })
        eq_(flagdata[self.old_av], {'da':
            ['fx1.0', {Action.ACCEPTED: self.actions[1].id}]
            })

    def testOneOldAndOtherNew(self):
        da = Locale.objects.get(code='da')
        de = Locale.objects.get(code='de')
        repo = self._setup(da, Action.ACCEPTED, None)
        eq_(repo.changesets.count(), 2)
        repo = self._setup(de, None, Action.ACCEPTED)
        eq_(repo.changesets.count(), 2)
        a4av, not_found = _actions4appversion(self.old_av,
                                              set([da.id, de.id]), 100)
        eq_(not_found, set([de.id]))
        eq_(a4av.keys(), [da.id])
        flag, action_id = a4av[da.id].items()[0]
        eq_(flag, Action.ACCEPTED)
        a4av, not_found = _actions4appversion(self.new_av,
                                              set([da.id, de.id]), 100)
        eq_(not_found, set([da.id]))
        eq_(a4av.keys(), [de.id])
        flag, action_id = a4av[de.id].items()[0]
        eq_(flag, Action.ACCEPTED)
        a4av, not_found = _actions4appversion(self.old_av,
                                              set([da.id, de.id]), 100)
        eq_(not_found, set([de.id]))
        eq_(a4av.keys(), [da.id])
        flag, action_id = a4av[da.id].items()[0]
        eq_(flag, Action.ACCEPTED)
        a4avs = actions4appversions(appversions=[self.new_av],
                                    locales=[da.id, de.id])
        eq_(len(a4avs), 2)
        ok_(self.old_av in a4avs)
        ok_(self.new_av in a4avs)
        a4av = a4avs[self.new_av]
        eq_(len(a4av), 1)
        a4av = a4avs[self.old_av]
        eq_(len(a4av), 1)
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {
            'da': ['fx1.0', {Action.ACCEPTED: self.actions[1].id}],
            'de': ['fx1.1', {Action.ACCEPTED: self.actions[3].id}]
            })
        eq_(flagdata[self.old_av], {
            'da': ['fx1.0', {Action.ACCEPTED: self.actions[1].id}]
            })

    def testOneOldObsoleted(self):
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, Action.OBSOLETED, None)
        eq_(repo.changesets.count(), 2)
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {})
        eq_(flagdata[self.old_av], {})

    def testOneOldObsoletedAndNew(self):
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, Action.OBSOLETED, Action.ACCEPTED)
        eq_(repo.changesets.count(), 3)
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {'da':
            ['fx1.1', {Action.ACCEPTED: self.actions[3].id}]
            })
        eq_(flagdata[self.old_av], {})

    def testOneOldAndNewObsoleted(self):
        locale = Locale.objects.get(code='da')
        repo = self._setup(locale, Action.ACCEPTED, Action.OBSOLETED)
        eq_(repo.changesets.count(), 3)
        flagdata = flags4appversions()
        ok_(self.old_av in flagdata)
        ok_(self.new_av in flagdata)
        eq_(len(flagdata), 2)
        eq_(flagdata[self.new_av], {})
        eq_(flagdata[self.old_av], {'da':
            ['fx1.0', {Action.ACCEPTED: self.actions[1].id}]
            })
