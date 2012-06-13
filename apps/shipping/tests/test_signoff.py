# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.tools import eq_, ok_
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.utils import simplejson as json
from commons.tests.mixins import EmbedsTestCaseMixin
from shipping.models import Milestone, AppVersion, Action
from shipping import api
from life.models import Locale, Push, Repository
from l10nstats.models import Run


class SignOffTest(TestCase, EmbedsTestCaseMixin):
    fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    def setUp(self):
        self.av = AppVersion.objects.get(code="fx1.0")
        api.test_locales.extend(range(1, 5))

    def tearDown(self):
        del api.test_locales[:]

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

    def test_status_json(self):
        """Test that the status json for the dashboard is OK"""
        url = reverse('shipping.views.status.status_json')
        response = self.client.get(url, {'av': 'fx1.0'})
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

    # XXX bug 763214, disable etag and test for now
    def _do_not_test_signoff_etag(self):
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
        Action.objects.create(
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
        tree = appver.trees_over_time.latest().tree
        pushes = (Push.objects
                  .filter(repository__forest__tree=tree)
                  .filter(repository__locale__code=locale.code)
                  .order_by('-pk'))
        last_push = pushes[0]
        Push.objects.create(
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
        Run.objects.create(
          tree=tree,
          locale=locale,
        )

        # that should force a new etag identifier
        response = self.client.get(url)
        eq_(response.status_code, 200)
        etag_before = etag
        etag = response.get('etag', None)
        ok_(etag != etag_before)

        # but not just any new run
        Run.objects.create(
          tree=tree,
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
