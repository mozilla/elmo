# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

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

from elmo_commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Repository, Push, Branch, File
from pushes import repo_fixtures
from pushes.utils import get_or_create_changeset
from pushes.utils import handlePushes, PushJS
from .base import mock_ui, RepoTestBase


class PushesTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_push_log(self):
        """basic test rendering the pushlog"""
        url = reverse('pushes:pushlog')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        # like I said, a very basic test


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
