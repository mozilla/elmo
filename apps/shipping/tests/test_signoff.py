# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import datetime
from nose.tools import eq_, ok_
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User, Permission
import json
from elmo_commons.tests.mixins import EmbedsTestCaseMixin
from shipping.models import (
    AppVersion,
    Action,
    Signoff,
    Application,
    AppVersionTreeThrough
)
from shipping import api
from life.models import (
    Locale,
    Push,
    Repository,
    Branch,
    Changeset,
    Tree,
    Forest
)
from shipping.views.signoff import SignoffView
import shipping.views.signoff
import shipping.views.status


class SignOffTest(TestCase, EmbedsTestCaseMixin):
    fixtures = ["test_repos.json", "test_pushes.json", "signoffs.json"]

    def setUp(self):
        self.av = AppVersion.objects.get(code="fx1.0")
        api.test_locales.extend(range(1, 5))

    def tearDown(self):
        del api.test_locales[:]

    def test_l10n_changesets(self):
        """Test that l10n-changesets is OK"""
        url = reverse('shipping-l10n_changesets')
        url += '?av=fx1.0'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, """da l10n da 0003
de l10n de 0002
""")
        ok_('max-age=60' in response['Cache-Control'])

    def test_shipped_locales(self):
        """Test that shipped-locales is OK"""
        url = reverse('shipping-shipped_locales')
        url += '?av=fx1.0'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, """da
de
en-US
""")
        ok_('max-age=60' in response['Cache-Control'])

    def test_status_json(self):
        """Test that the status json for the dashboard is OK"""
        url = reverse('shipping-status_json')
        response = self.client.get(url, {'av': 'fx1.0'})
        eq_(response.status_code, 200)
        ok_('max-age=60' in response['Cache-Control'])
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
        eq_(so['tree'], 'fx')
        ok_('fx/de' in sos)
        so = sos['fx/de']
        eq_(so['signoff'], ['accepted'])
        eq_(so['tree'], 'fx')
        ok_('fx/fr' in sos)
        so = sos['fx/fr']
        eq_(so['signoff'], ['rejected'])
        eq_(so['tree'], 'fx')
        ok_('fx/pl' in sos)
        so = sos['fx/pl']
        eq_(so['signoff'], ['pending'])
        eq_(so['tree'], 'fx')

    def test_dashboard_static_files(self):
        """render the shipping dashboard and check that all static files are
        accessible"""
        url = reverse(shipping.views.dashboard)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_signoff_static_files(self):
        """render the signoffs page and chek that all static files work"""
        url = reverse('shipping-signoff',
                      args=['de', self.av.code])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_redirect_signoff_locale(self):
        locale = Locale.objects.get(code='de')

        url = reverse(shipping.views.signoff.signoff_locale, args=['xxx'])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse(shipping.views.signoff.signoff_locale,
                      args=[locale.code])

        response = self.client.get(url)
        eq_(response.status_code, 301)  # permanent
        self.assertRedirects(
            response,
            reverse('l10n-team', args=[locale.code]),
            status_code=301
        )

        # lastly, take a perfectly healthy signoff URL
        url = reverse('shipping-signoff',
                      args=[locale.code, self.av.code])
        eq_(self.client.get(url).status_code, 200)

        # peal off the AppVersion code
        url = url.replace(self.av.code, '')
        assert url.endswith('/')
        eq_(self.client.get(url).status_code, 301)

        # same thing if we drop the trailing /
        url = url[:-1]
        assert url.endswith(locale.code)
        eq_(self.client.get(url).status_code, 301)

        # and remove the locale too and enter a rabbit hole
        url = url.replace(locale.code, '')
        eq_(self.client.get(url).status_code, 404)

    def test_signoff_rows_invalid_next_push_date(self):
        url = reverse('shipping-signoff-rows',
                      args=['de', self.av.code])
        response = self.client.get(url)
        # missing the push_date GET parameter
        eq_(response.status_code, 400)

        response = self.client.get(url, {'push_date': 'xxx'})
        # not a valid date
        eq_(response.status_code, 400)

    def test_signoff_rows(self):
        url = reverse('shipping-signoff-rows',
                      args=['de', self.av.code])
        p1, p2, p3 = Push.objects.all().order_by('push_date')[:3]
        next_push_date = p3.push_date.isoformat()
        response = self.client.get(url, {'push_date': next_push_date})
        eq_(response.status_code, 200)
        eq_(response['content-type'], 'application/json; charset=UTF-8')
        structure = json.loads(response.content)
        ok_(structure['html'])
        ok_(not structure['pushes_left'])

    def test_cancel_pending_signoff(self):
        appver, = AppVersion.objects.all()
        # gotta know your signoffs.json
        accepted = Signoff.objects.get(appversion=appver,
                                       locale__code='de')
        assert accepted.status == Action.ACCEPTED

        cancel_url = reverse(shipping.views.signoff.cancel_signoff,
                             args=['de', appver.code])

        # only accepts POST
        eq_(self.client.get(cancel_url).status_code, 405)

        # 302 because you're not logged in
        response = self.client.post(cancel_url, {'signoff_id': accepted.pk})
        eq_(response.status_code, 302)

        user = User.objects.get(username='l10ndriver')
        user.set_password('secret')
        user.save()
        assert self.client.login(username=user.username, password='secret')

        # 302 because you don't have the review_signoff permission
        response = self.client.post(cancel_url, {'signoff_id': accepted.pk})
        eq_(response.status_code, 302)

        user.user_permissions.add(
            Permission.objects.get(codename='add_signoff')
        )

        # not a recognized appversion code
        junk_url = cancel_url.replace(appver.code, 'xxx')
        eq_(self.client.post(junk_url).status_code, 404)

        # no signoff_id
        response = self.client.post(cancel_url, {})
        eq_(response.status_code, 400)

        # bogus signoff_id
        response = self.client.post(cancel_url, {'signoff_id': 'xxx'})
        eq_(response.status_code, 400)

        # not found signoff_id
        response = self.client.post(cancel_url, {'signoff_id': 999})
        eq_(response.status_code, 400)

        # 400 because it's already accepted
        response = self.client.post(cancel_url, {'signoff_id': accepted.pk})
        eq_(response.status_code, 400)

        # pl has a pending signoff
        cancel_url = reverse(shipping.views.signoff.cancel_signoff,
                             args=['pl', appver.code])
        signoff = Signoff.objects.get(appversion=appver,
                                      locale__code='pl')

        assert Action.objects.filter(signoff=signoff).count()
        response = self.client.post(cancel_url, {'signoff_id': signoff.pk})
        eq_(response.status_code, 302)
        eq_(Action.objects.filter(signoff=signoff).count(), 2)

        signoff = Signoff.objects.get(pk=signoff.pk)
        eq_(signoff.status, Action.CANCELED)

    def test_reopen_canceled_signoff(self):
        appver, = AppVersion.objects.all()
        # gotta know your signoffs.json
        accepted = Signoff.objects.get(appversion=appver,
                                      locale__code='de')
        assert accepted.status == Action.ACCEPTED
        reopen_url = reverse(shipping.views.signoff.reopen_signoff,
                             args=['de', appver.code])

        # only accepts POST
        eq_(self.client.get(reopen_url).status_code, 405)

        # 302 because you're not logged in
        response = self.client.post(reopen_url, {'signoff_id': accepted.pk})
        eq_(response.status_code, 302)

        user = User.objects.get(username='l10ndriver')
        user.set_password('secret')
        user.save()
        assert self.client.login(username=user.username, password='secret')

        # 302 because you don't have the review_signoff permission
        response = self.client.post(reopen_url, {'signoff_id': accepted.pk})
        eq_(response.status_code, 302)

        user.user_permissions.add(
            Permission.objects.get(codename='add_signoff')
        )

        # not a recognized appversion code
        junk_url = reopen_url.replace(appver.code, 'xxx')
        eq_(self.client.post(junk_url).status_code, 404)

        # no signoff_id
        response = self.client.post(reopen_url, {})
        eq_(response.status_code, 400)

        # bogus signoff_id
        response = self.client.post(reopen_url, {'signoff_id': 'xxx'})
        eq_(response.status_code, 400)

        # not found signoff_id
        response = self.client.post(reopen_url, {'signoff_id': 999})
        eq_(response.status_code, 400)

        # 400 because it's already accepted
        response = self.client.post(reopen_url, {'signoff_id': accepted.pk})
        eq_(response.status_code, 400)

        # pl has a pending signoff
        Action.objects.create(
            signoff=accepted,
            flag=Action.CANCELED,
            author=User.objects.exclude(pk=user.pk)[0]  # anybody else
        )
        signoff = Signoff.objects.get(pk=accepted.pk)
        assert signoff.status == Action.CANCELED

        assert Action.objects.filter(signoff=signoff).count()
        response = self.client.post(reopen_url, {'signoff_id': signoff.pk})
        eq_(response.status_code, 302)

        signoff = Signoff.objects.get(pk=signoff.pk)
        eq_(signoff.status, Action.PENDING)

    def test_signoff_annotated_pushes(self):
        view = SignoffView()
        locale = Locale.objects.get(code='de')

        real_av, flags = (api.flags4appversions([self.av],
            locales=[locale.id])
                          .get(self.av, {})
                          .get(locale.code, [None, {}]))
        actions = list(Action.objects.filter(id__in=flags.values())
                       .select_related('signoff__push__repository', 'author'))
        fallback, = actions
        assert fallback.flag == Action.ACCEPTED, fallback.flag
        pushes_data = view.annotated_pushes(
            locale,
            self.av,
            actions=actions,
            flags=flags,
            fallback=fallback,
        )
        suggested_signoff = pushes_data['suggested_signoff']
        eq_(suggested_signoff, None)
        pushes = pushes_data['pushes']
        changesets = [c for p in pushes for c in p['changes']]
        revisions = [x.revision for x in changesets]
        # only `de` changes in the right order
        eq_(revisions, [u'l10n de 0003', u'l10n de 0002'])


class SignOffAnnotatedPushesTest(TestCase):
    fixtures = ['test_repos.json']

    def setUp(self):
        _forest = Forest.objects.get(name='l10n')
        _tree = Tree.objects.create(code='fx', l10n=_forest)
        _app = Application.objects.create(name='Firefox', code='fx')
        self.av = AppVersion.objects.create(
            app=_app,
            version='1.0',
            code='fx1.0',
        )
        AppVersionTreeThrough.objects.create(
            start=None,
            tree=_tree,
            appversion=self.av,
            end=None,
        )
        self.locale = Locale.objects.get(code='de')
        self.peter = User.objects.create_user(
            'peter', 'peter@mozilla.com', 'secret'
        )
        self.axel = User.objects.create_user(
            'axel', 'axel@mozilla.com', 'secret'
        )

        repository, = Repository.objects.filter(locale=self.locale)
        first_date = datetime.datetime.utcnow() - datetime.timedelta(days=12)
        branch, = Branch.objects.all()
        self.pushes = []
        for i in range(1, 6):
            push = Push.objects.create(
                user='Bob',
                repository=repository,
                push_date=first_date + datetime.timedelta(days=i),
                push_id=i + 1
            )
            change = Changeset.objects.create(
                revision='abc123-%d' % i,
                user='user@example.tld',
                description='Description%d' % i,
                branch=branch
            )
            push.changesets.add(change)
            self.pushes.append(push)

    def _get_flags_and_actions(self):
        __, flags = (api.flags4appversions([self.av],
            locales=[self.locale.id])
                          .get(self.av, {})
                          .get(self.locale.code, [None, {}]))
        actions = Action.objects.filter(id__in=flags.values())
        return flags, actions

    def test_5_pushes_no_fallback(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            count=1
        )
        pushes = pushes_data['pushes']
        # there are more pushes than this but it gets limited
        # by `count` instead because there is no fallback
        eq_(len(pushes), 1)
        eq_(pushes_data['pushes_left'], 4)

        # equally...
        # the `count` is what determines how many we get back
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            count=3
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 3)
        eq_(pushes_data['pushes_left'], 2)

    def test_5_pushes_2nd_accepted(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        # Let's make an accepted signoff on the 2nd push
        push = self.pushes[1]
        signoff = Signoff.objects.create(
            push=push,
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.ACCEPTED,
            author=self.peter,
        )

        flags, actions = self._get_flags_and_actions()
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            count=1
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 4)
        eq_(pushes_data['pushes_left'], 1)
        # the last (aka. first) one should have a signoff with an
        # action on that is accepting
        eq_(pushes[-1]['signoffs'][0]['action'].flag, Action.ACCEPTED)

    def test_5_pushes_2nd_accepted_3rd_rejected(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        # Let's make an accepted signoff on the 2nd push
        push = self.pushes[1]
        signoff = Signoff.objects.create(
            push=push,
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.ACCEPTED,
            author=self.peter,
        )

        # Let's make a rejected signoff on the 3rd push
        push = self.pushes[2]
        signoff = Signoff.objects.create(
            push=push,
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.REJECTED,
            author=self.peter,
        )

        flags, actions = self._get_flags_and_actions()
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            count=1
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 4)
        eq_(pushes_data['pushes_left'], 1)
        # the last (aka. first) one should have a signoff with an
        # action on that is accepting
        eq_(pushes[-1]['signoffs'][0]['action'].flag, Action.ACCEPTED)

    def test_5_pushes_2nd_accepted_3rd_rejected_4th_pending(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        # make an accepted signoff on the 2nd push
        signoff = Signoff.objects.create(
            push=self.pushes[1],
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.ACCEPTED,
            author=self.peter,
        )

        # make a rejected signoff on the 3rd push
        signoff = Signoff.objects.create(
            push=self.pushes[2],
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.REJECTED,
            author=self.peter,
        )

        # make a pending signoff on the 4th push
        signoff = Signoff.objects.create(
            push=self.pushes[3],
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.PENDING,
            author=self.peter,
        )

        flags, actions = self._get_flags_and_actions()
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            count=1
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 4)
        eq_(pushes_data['pushes_left'], 1)
        # the last (aka. first) one should have a signoff with an
        # action on that is accepting
        eq_(pushes[-1]['signoffs'][0]['action'].flag, Action.ACCEPTED)

    def test_5_pushes_3rd_rejected_4th_pending(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        # make a rejected signoff on the 3rd push
        signoff = Signoff.objects.create(
            push=self.pushes[2],
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.REJECTED,
            author=self.peter,
        )

        # make a pending signoff on the 4th push
        signoff = Signoff.objects.create(
            push=self.pushes[3],
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.PENDING,
            author=self.peter,
        )

        flags, actions = self._get_flags_and_actions()
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            count=1
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 4)
        eq_(pushes_data['pushes_left'], 1)

        # the last (aka. first) one should have a signoff with an
        # action on that is rejected
        eq_(pushes[-2]['signoffs'][0]['action'].flag, Action.REJECTED)

    def test_5_pushes_1st_pending(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        # make a pending signoff on the 1st push
        signoff = Signoff.objects.create(
            push=self.pushes[0],
            appversion=self.av,
            author=self.axel,
            locale=self.locale,
        )
        Action.objects.create(
            signoff=signoff,
            flag=Action.PENDING,
            author=self.peter,
        )

        flags, actions = self._get_flags_and_actions()
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            fallback=None,
            count=1
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 5)
        eq_(pushes_data['pushes_left'], 0)

        # the last (aka. first) one should have a signoff with an
        # action on that is rejected
        eq_(pushes[-1]['signoffs'][0]['action'].flag, Action.PENDING)

    def test_next_push_date(self):
        view = SignoffView()
        flags, actions = self._get_flags_and_actions()

        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            fallback=None,
            count=2
        )
        pushes = pushes_data['pushes']
        # there are more pushes than this but it gets limited
        # by `count` instead because there is no fallback
        eq_(len(pushes), 2)
        # because there are 5 in this fixture, we can expect...
        eq_(pushes_data['pushes_left'], 3)

        p1, p2, p3, p4, p5 = Push.objects.all().order_by('push_date')
        eq_(p4.push_date, pushes_data['next_push_date'])

        # get the next two
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            fallback=None,
            count=2,
            next_push_date=pushes_data['next_push_date']
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 2)
        eq_(pushes_data['pushes_left'], 1)

        eq_(p2.push_date, pushes_data['next_push_date'])

        # and get the last remaining one
        pushes_data = view.annotated_pushes(
            self.locale,
            self.av,
            actions=actions,
            flags=flags,
            fallback=None,
            count=2,
            next_push_date=pushes_data['next_push_date']
        )
        pushes = pushes_data['pushes']
        eq_(len(pushes), 1)
        eq_(pushes_data['pushes_left'], 0)

        eq_(p1.push_date, pushes_data['next_push_date'])
