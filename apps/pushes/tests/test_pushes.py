# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import datetime
import time
import json
from nose.tools import eq_, ok_
from elmo.test import TestCase
from django import http
from django.core.urlresolvers import reverse
from mercurial import commands as hgcommands
from mercurial.hg import repository
from mercurial.error import RepoError, RepoLookupError

from commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Repository, Push, Branch, File
from pushes import repo_fixtures
from pushes.utils import get_or_create_changeset
from pushes.views.api import jsonify
from pushes.utils import handlePushes, PushJS
from .base import mock_ui, RepoTestBase


class PushesTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_push_log(self):
        """basic test rendering the pushlog"""
        url = reverse('pushes.views.pushlog')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        # like I said, a very basic test


class JSONifyTestCase(TestCase):
    def test_json(self):
        ref = {
            'foo': [1, 2, 3],
            '12': "string"
            }
        response = jsonify(lambda r: r)(ref)
        ok_(isinstance(response, http.HttpResponse))
        ok_(response.status_code, 200)
        eq_(response["Access-Control-Allow-Origin"], "*")
        r_data = json.loads(response.content)
        eq_(r_data, ref)

    def test_fail(self):
        ref = http.HttpResponseBadRequest('oh picky')
        response = jsonify(lambda r: r)(ref)
        eq_(response["Access-Control-Allow-Origin"], "*")
        eq_(ref, response)


class ApiTestCase(RepoTestBase):

    def setUp(self):
        super(ApiTestCase, self).setUp()
        self.repo_data = repo_fixtures.network(self._base)
        for name, hgrepo in self.repo_data['repos'].iteritems():
            dbrepo = Repository.objects.create(
                name=name,
                url='http://localhost:8001/%s/' % name
            )
            for i in hgrepo:
                get_or_create_changeset(dbrepo, hgrepo, hgrepo[i].hex())

    def test_network(self):
        '''test the basic output of the network api'''
        url = reverse('pushes.views.api.network')
        response = self.client.get(url, {
            'revision': self.repo_data['forks'][0]
            })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        id4rev = dict((c['revision'], c['id'])
                      for c in data['changesets'].itervalues())
        ref_forks = map(lambda r: str(id4rev[r]), self.repo_data['forks'])
        children = data['children']
        for f in ref_forks:
            ok_(len(children[f]) > 1)

        ref_heads = map(lambda r: str(id4rev[r]), self.repo_data['heads'])
        for h in ref_heads:
            ok_(h not in children)

    def test_fork(self):
        '''test the basic output of the network api'''
        repo = self.repo_data['repos'].keys()[0]
        url = reverse('pushes.views.api.forks', args=[repo])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['repo'], repo)
        ok_(data['revision'] in self.repo_data['heads'])


class TestHandlePushes(RepoTestBase):

    def setUp(self):  # copied from DiffTestCase
        super(TestHandlePushes, self).setUp()
        self.repo_name = 'mozilla-central-original'
        self.repo = os.path.join(self._base, self.repo_name)

    def test_handlePushes(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file:///' + self.repo
        )
        self.assertEqual(handlePushes(repo.pk, []), None)

        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             '''))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        timestamp = int(time.time())
        push_id = 100
        username = 'jdoe'
        pushjs0 = PushJS(push_id, {
          'date': timestamp,
          'changesets': [rev0],
          'user': username,
        })
        result = handlePushes(repo.pk, [pushjs0])
        self.assertEqual(result, 1)

        # expect all of these to have been created
        push, = Push.objects.all()
        branch, = Branch.objects.all()
        changeset, = push.changesets.all()

        self.assertEqual(push.repository, repo)
        self.assertEqual(push.push_id, push_id)
        self.assertEqual(push.user, username)
        self.assertEqual(push.push_date.strftime('%Y%m%d%H%M'),
                         datetime.datetime.utcnow().strftime('%Y%m%d%H%M'))

        self.assertEqual(changeset.description, 'initial commit')
        self.assertEqual(changeset.user, 'Jane Doe <jdoe@foo.tld>')
        self.assertEqual(changeset.revision, rev0)
        self.assertEqual(changeset.branch, branch)

        self.assertEqual(branch.name, 'default')

    def test_handlePushes_messedup_revisions(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file:///' + self.repo
        )
        self.assertEqual(handlePushes(repo.pk, []), None)

        ui = mock_ui()

        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             '''))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
          'date': timestamp,
          'changesets': [rev0[::-1]],
          'user': 'jdoe',
        })
        self.assertRaises(RepoLookupError, handlePushes,
                          repo.pk, [pushjs0])

    def test_handlePushes_space_files(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file:///' + self.repo
        )
        self.assertEqual(handlePushes(repo.pk, []), None)

        ui = mock_ui()

        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.dtd '), 'w')  # deliberate trailing space
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             '''))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
          'date': timestamp,
          'changesets': [rev0],
          'user': 'jdoe',
        })
        handlePushes(repo.pk, [pushjs0])

        file_, = File.objects.all()
        self.assertEqual(file_.path, 'file.dtd ')

    def test_handlePushes_repeated(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file:///' + self.repo
        )
        self.assertEqual(handlePushes(repo.pk, []), None)

        ui = mock_ui()

        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             '''))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
          'date': timestamp,
          'changesets': [rev0],
          'user': 'jdoe',
        })
        # first time
        pushes_initial = Push.objects.all().count()
        result = handlePushes(repo.pk, [pushjs0])
        self.assertEqual(result, 1)
        pushes_after = Push.objects.all().count()
        self.assertEqual(pushes_initial, pushes_after - 1)

        # a second time should be harmless
        result = handlePushes(repo.pk, [pushjs0])
        self.assertEqual(result, 1)
        pushes_after_after = Push.objects.all().count()
        self.assertEqual(pushes_after, pushes_after_after)

    def test_handlePushes_cause_repoerror(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file:///does/not/exist'
        )
        self.assertEqual(handlePushes(repo.pk, []), None)

        ui = mock_ui()

        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             '''))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
          'date': timestamp,
          'changesets': [rev0],
          'user': 'jdoe',
        })
        self.assertRaises(RepoError, handlePushes,
                          repo.pk, [pushjs0])

    def test_handlePushes_twice(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file://' + self.repo
        )

        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             '''))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
          'date': timestamp,
          'changesets': [rev0],
          'user': 'jdoe',
        })
        result = handlePushes(repo.pk, [pushjs0])

        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             <!ENTITY key3 "World">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        # a second time
        timestamp = int(time.time())
        pushjs0 = PushJS(101, {
          'date': timestamp,
          'changesets': [rev1],
          'user': 'jdoe',
        })

        # re-fetch
        repo = Repository.objects.get(pk=repo.pk)
        self.assertEqual(repo.changesets.all().count(), 2)

        result = handlePushes(repo.pk, [pushjs0])
        self.assertEqual(result, 1)

        # re-fetch
        repo = Repository.objects.get(pk=repo.pk)
        self.assertEqual(repo.changesets.all().count(), 3)
