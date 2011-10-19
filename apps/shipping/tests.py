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

'''Tests for the shipping.
'''
from django.test import TestCase
from django.core.urlresolvers import reverse
from shipping.models import Milestone, Application, AppVersion, Signoff, Action
from shipping.api import signoff_actions, flag_lists
from life.models import Tree, Forest, Locale, Push, Repository
from l10nstats.models import Run
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import simplejson as json
from commons.tests.mixins import EmbedsTestCaseMixin
from nose.tools import eq_, ok_


class ShippingTestCaseBase(TestCase, EmbedsTestCaseMixin):

    def _create_appver_milestone(self):
        app = Application.objects.create(
          name='firefox',
          code='fx'
        )
        l10n = Forest.objects.create(
          name='l10n-central',
          url='http://hg.mozilla.org/l10n-central/',
        )
        tree = Tree.objects.create(
          code='fx',
          l10n=l10n,
        )
        appver = AppVersion.objects.create(
          app=app,
          version='1',
          code='fx1',
          codename='foxy',
          tree=tree,
        )
        milestone = Milestone.objects.create(
          code='one',
          name='One',
          appver=appver,
        )

        return appver, milestone


class ShippingTestCase(ShippingTestCaseBase):

    def test_basic_render_index_page(self):
        """render the shipping index page"""
        url = reverse('shipping.views.index')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_basic_render_app_changes(self):
        """render shipping.views.app.changes"""
        url = reverse('shipping.views.app.changes',
                      args=['junk'])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        appver, milestone = self._create_appver_milestone()
        url = reverse('shipping.views.app.changes',
                      args=[appver.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('<title>Locale changes for %s' % appver in response.content)
        ok_('<h1>Locale changes for %s' % appver in response.content)

    def test_basic_render_confirm_drill_mstone(self):
        """render shipping.views.confirm_drill_mstone"""
        url = reverse('shipping.views.confirm_drill_mstone')
        response = self.client.get(url)
        eq_(response.status_code, 404)
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302) # not permission to view

        admin = User.objects.create_user(
          username='admin',
          email='admin@mozilla.com',
          password='secret',
        )
        admin.user_permissions.add(
          Permission.objects.get(codename='can_ship')
        )
        assert self.client.login(username='admin', password='secret')
        response = self.client.get(url, {'ms': 'junk'})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302)

        milestone.status = 1
        milestone.save()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 200)

        self.assert_all_embeds(response.content)
        ok_('<title>Shipping %s' % milestone in response.content)
        ok_('<h1>Shipping %s' % milestone in response.content)

    def test_basic_render_confirm_ship_mstone(self):
        """render shipping.views.confirm_ship_mstone"""
        url = reverse('shipping.views.confirm_ship_mstone')
        response = self.client.get(url)
        eq_(response.status_code, 404)
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302) # not permission to view

        # Note how confirm doesn't require the 'can_ship' permission even though
        # the POST to actually ship does require the permission. The reason
        # for this is because the confirmation page has been used to summorize
        # what can be shipped and this URL is shared with people outside this
        # permission.
        # In fact, you don't even need to be logged in.

        response = self.client.get(url, {'ms': 'junk'})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 302)

        milestone.status = 1
        milestone.save()
        response = self.client.get(url, {'ms': milestone.code})
        eq_(response.status_code, 200)

        self.assert_all_embeds(response.content)
        ok_('<title>Shipping %s' % milestone in response.content)
        ok_('<h1>Shipping %s' % milestone in response.content)

    def test_dashboard_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.dashboard')
        # Fail
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()

        # Succeed
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_l10n_changesets_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.status.l10n_changesets')
        # Fail
        response = self.client.get(url, dict(ms=""))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        eq_(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_shipped_locales_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.status.shipped_locales')
        # Fail
        response = self.client.get(url, dict(ms=""))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        eq_(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_signoff_json_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.status.signoff_json')
        # Fail
        response = self.client.get(url, dict(ms=""))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av=""))
        eq_(response.status_code, 404)

        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)
        response = self.client.get(url, dict(av="junk"))
        eq_(response.status_code, 404)

        # to succeed we need sample fixtures
        appver, milestone = self._create_appver_milestone()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)
        response = self.client.get(url, dict(av=appver.code))
        eq_(response.status_code, 200)

    def test_confirm_ship_mstone_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.confirm_ship_mstone')

        admin = User.objects.create_user(
          username='admin',
          email='admin@mozilla.com',
          password='secret',
        )
        admin.user_permissions.add(
          Permission.objects.get(codename='can_ship')
        )
        assert self.client.login(username='admin', password='secret')

        # Fail
        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 404)

        # Succeed
        __, milestone = self._create_appver_milestone()
        milestone.status = 1
        milestone.save()
        response = self.client.get(url, dict(ms=milestone.code))
        eq_(response.status_code, 200)

    def test_ship_mstone_bad_urls(self):
        """test that bad GET parameters raise 404 errors not 500s"""
        url = reverse('shipping.views.ship_mstone')
        # Fail
        response = self.client.get(url, dict(ms="junk"))
        eq_(response.status_code, 405)
        response = self.client.post(url, dict(ms="junk"))
        # redirects because we're not logged and don't have the permission
        eq_(response.status_code, 302)

        milestone_content_type, __ = ContentType.objects.get_or_create(
          name='milestone',
        )
        perm, __ = Permission.objects.get_or_create(
          name='Can ship a Milestone',
          content_type=milestone_content_type,
          codename='can_ship'
        )
        admin = User.objects.create(
          username='admin',
        )
        admin.set_password('secret')
        admin.user_permissions.add(perm)
        admin.save()
        assert self.client.login(username='admin', password='secret')

        __, milestone = self._create_appver_milestone()
        response = self.client.post(url, dict(ms="junk"))
        eq_(response.status_code, 404)

        milestone.status = Milestone.OPEN
        milestone.save()
        response = self.client.post(url, dict(ms=milestone.code))
        eq_(response.status_code, 302)

        milestone = Milestone.objects.get(code=milestone.code)
        eq_(milestone.status, 2)

    def test_milestones_static_files(self):
        """render the milestones page and check all static files"""
        url = reverse('shipping.views.milestones')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_about_milestone_static_files(self):
        """render the about milestone page and check all static files"""
        url = reverse('shipping.views.milestone.about',
                      args=['junk'])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        __, milestone = self._create_appver_milestone()
        url = reverse('shipping.views.milestone.about',
                      args=[milestone.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)


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


class SignOffTest(TestCase, EmbedsTestCaseMixin):
    fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    def setUp(self):
        self.av = AppVersion.objects.get(code="fx1.0")

    def test_l10n_changesets(self):
        """Test that l10n-changesets is OK"""
        url = reverse('shipping.views.status.l10n_changesets')
        url += '?av=fx1.0'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, """da l10n da 0003
de l10n de 0002
""")

    def test_shipped_locales(self):
        """Test that shipped-locales is OK"""
        url = reverse('shipping.views.status.shipped_locales')
        url += '?av=fx1.0'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, """da
de
en-US
""")

    def test_signoff_json(self):
        """Test that the signoff json for the dashboard is OK"""
        url = reverse('shipping.views.status.signoff_json')
        url += '?av=fx1.0'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_('items' in data)
        items = data['items']
        eq_(len(items), 5)
        sos = {}
        avt = None
        for item in items:
            if item['type'] == 'SignOff':
                sos[item['label']] = item
            elif item['type'] == 'AppVer4Tree':
                avt = item
            else:
                eq_(item, None)
        eq_(avt['appversion'], 'fx1.0')
        eq_(avt['label'], 'fx')
        ok_('fx/da' in sos)
        so = sos['fx/da']
        eq_(so['signoff'], ['accepted', 'pending'])
        eq_(so['apploc'], 'fx::da')
        eq_(so['tree'], 'fx')
        ok_('fx/de' in sos)
        so = sos['fx/de']
        eq_(so['signoff'], ['accepted'])
        eq_(so['apploc'], 'fx::de')
        eq_(so['tree'], 'fx')
        ok_('fx/fr' in sos)
        so = sos['fx/fr']
        eq_(so['signoff'], ['rejected'])
        eq_(so['apploc'], 'fx::fr')
        eq_(so['tree'], 'fx')
        ok_('fx/pl' in sos)
        so = sos['fx/pl']
        eq_(so['signoff'], ['pending'])
        eq_(so['apploc'], 'fx::pl')
        eq_(so['tree'], 'fx')

    def test_ship_milestone(self):
        """Go through a shipping cycle and verify the results"""
        mile = self.av.milestone_set.create(code='fx1.0b1',
                                            name='Build 1')
        releng = User.objects.create_user(
            username='fxbld',
            email='fxbld@mozilla.com',
            password='secret',
        )
        releng.user_permissions.add(
            Permission.objects.get(codename='can_ship'),
            Permission.objects.get(codename='can_open')
        )
        assert self.client.login(username='fxbld', password='secret')
        ship = reverse('shipping.views.ship_mstone')
        response = self.client.post(ship, {'ms': mile.code})
        eq_(response.status_code, 403)
        _open = reverse('shipping.views.open_mstone')
        response = self.client.post(_open, {'ms': mile.code})
        eq_(response.status_code, 302)
        response = self.client.post(ship, {'ms': mile.code})
        eq_(response.status_code, 302)
        mile = self.av.milestone_set.all()[0]  # refresh mile from the db
        eq_(mile.status, Milestone.SHIPPED)
        eq_(mile.signoffs.count(), 2)
        # now that it's shipped, it should error to ship again
        response = self.client.post(ship, {'ms': mile.code})
        eq_(response.status_code, 403)
        # verify l10n-changesets and json, and shipped-locales
        url = reverse('shipping.views.status.l10n_changesets')
        response = self.client.get(url, {'ms': mile.code})
        eq_(response.status_code, 200)
        eq_(response.content, "da l10n da 0003\nde l10n de 0002\n")
        url = reverse('shipping.views.milestone.json_changesets')
        response = self.client.get(url, {'ms': mile.code,
                                         'platforms': 'windows, linux'})
        eq_(response.status_code, 200)
        json_changes = json.loads(response.content)
        eq_(json_changes, {'de':
                            {
                                'revision': 'l10n de 0002',
                                'platforms': ['windows', 'linux']
                            },
                            'da':
                            {
                               'revision': 'l10n da 0003',
                               'platforms': ['windows', 'linux']
                            }
                           })
        url = reverse('shipping.views.status.shipped_locales')
        response = self.client.get(url, {'ms': mile.code})
        eq_(response.status_code, 200)
        eq_(response.content, "da\nde\nen-US\n")


    def test_dashboard_static_files(self):
        """render the shipping dashboard and check that all static files are
        accessible"""
        url = reverse('shipping.views.dashboard')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_signoff_static_files(self):
        """render the signoffs page and chek that all static files work"""
        url = reverse('shipping.views.signoff.signoff',
                      args=['de', self.av.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_signoff_etag(self):
        """Test that the ETag is sent correctly for the signoff() view.

        Copied here from the etag_signoff() function's doc string:
            The signoff view should update for:
                - new actions
                - new pushes
                - new runs on existing pushes
                - changed permissions

        So, we need to make this test check all of that.
        """
        appver = self.av
        locale = Locale.objects.get(code='de')
        url = reverse('shipping.views.signoff.signoff',
                      args=[locale.code, appver.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag = response.get('etag', None)
        ok_(etag)

        # expect the PK of the most recent action to be in the etag
        actions = (Action.objects
          .filter(signoff__locale__code=locale.code,
                  signoff__appversion__code=appver.code)
          .order_by('-pk'))
        last_action = actions[0]

        # now, log in and expect the ETag to change once the user has the
        # right permissions
        user = User.objects.get(username='l10ndriver')  # from fixtures
        user.set_password('secret')
        user.save()
        assert self.client.login(username='l10ndriver', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag)
        eq_(etag, etag_before)

        add_perm = Permission.objects.get(codename='add_signoff')
        user.user_permissions.add(add_perm)
        user.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)

        add_perm = Permission.objects.get(codename='review_signoff')
        user.user_permissions.add(add_perm)
        user.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)

        # add a new action
        new_last_action = Action.objects.create(
          signoff=last_action.signoff,
          flag=last_action.flag,
          author=user,
          comment='test'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)

        # add a new push
        assert Push.objects.all()
        # ...by copying the last one
        pushes = (Push.objects
                  .filter(repository__forest__tree=appver.tree_id)
                  .filter(repository__locale__code=locale.code)
                  .order_by('-pk'))
        last_push = pushes[0]
        push = Push.objects.create(
          repository=last_push.repository,
          user=last_push.user,
          push_date=last_push.push_date,
          push_id=last_push.push_id + 1
        )

        # that should force a new etag identifier
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)

        # but not if a new, unreleated push is created
        other_locale = Locale.objects.get(code='pl')
        other_repo = Repository.objects.get(locale=other_locale)

        Push.objects.create(
          repository=other_repo,
          user=last_push.user,
          push_date=last_push.push_date,
          push_id=last_push.push_id + 1
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        # doesn't change the etag since the *relevant* pushes haven't changed
        ok_(etag == etag_before)

        # add a new run
        assert not Run.objects.all().exists()  # none in fixtures
        # ...again, by copying the last one and making a small change
        run = Run.objects.create(
          tree=appver.tree,
          locale=locale,
        )

        # that should force a new etag identifier
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)

        # but not just any new run
        run = Run.objects.create(
          tree=appver.tree,
          locale=other_locale,
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        # not different this time!
        ok_(etag == etag_before)

        # lastly, log out and it should ne different
        self.client.logout()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)
