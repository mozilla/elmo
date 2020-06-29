# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import mock
import time
from elmo.test import TestCase
from django.urls import reverse
import hglib

from elmo_commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Repository, Push, Branch, File
from pushes.utils import handlePushes, PushJS
from .base import RepoTestBase


class PushesTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_push_log(self):
        """basic test rendering the pushlog"""
        url = reverse('pushes:pushlog')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)
        # like I said, a very basic test


@mock.patch('pushes.utils.logging', mock.MagicMock())
class TestHandlePushes(RepoTestBase):

    repo_name = 'mozilla-central-original'

    def test_handlePushes(self):
        repo = Repository.objects.create(
          name='mozilla-central',
          url='file:///' + self.repo
        )

        with hglib.init(self.repo).open() as hgrepo:
            with open(hgrepo.pathto('file.dtd'), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                ''')

            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="initial commit",
                          addremove=True)
            rev0 = hgrepo[0].node().decode('ascii')

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
        self.assertEqual(
            push.push_date,
            datetime.datetime.utcfromtimestamp(timestamp)
        )

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

        with hglib.init(self.repo).open() as hgrepo:
            with open(hgrepo.pathto('file.dtd'), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                ''')

            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="initial commit",
                          addremove=True)
            rev0 = hgrepo[0].node().decode('ascii')

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
            'date': timestamp,
            'changesets': [rev0[::-1]],
            'user': 'jdoe',
        })
        self.assertRaises(KeyError, handlePushes,
                          repo.pk, [pushjs0])

    def test_handlePushes_space_files(self):
        repo = Repository.objects.create(
            name='mozilla-central',
            url='file:///' + self.repo
        )

        with hglib.init(self.repo).open() as hgrepo:
            # deliberate trailing space in file name
            with open(hgrepo.pathto('file.dtd '), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                ''')

            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="initial commit",
                          addremove=True)
            rev0 = hgrepo[0].node().decode('ascii')

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

        with hglib.init(self.repo).open() as hgrepo:
            with open(hgrepo.pathto('file.dtd'), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                ''')

            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="initial commit",
                          addremove=True)
            rev0 = hgrepo[0].node().decode('ascii')

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

        with hglib.init(self.repo).open() as hgrepo:
            with open(hgrepo.pathto('file.dtd'), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                ''')

            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="initial commit",
                          addremove=True)
            rev0 = hgrepo[0].node().decode('ascii')

        timestamp = int(time.time())
        pushjs0 = PushJS(100, {
            'date': timestamp,
            'changesets': [rev0],
            'user': 'jdoe',
        })
        self.assertRaises(hglib.error.CommandError, handlePushes,
                          repo.pk, [pushjs0])

    def test_handlePushes_twice(self):
        repo = Repository.objects.create(
            name='mozilla-central',
            url='file://' + self.repo
        )

        with hglib.init(self.repo).open() as hgrepo:
            with open(hgrepo.pathto('file.dtd'), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                ''')

            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="initial commit",
                          addremove=True)
            rev0 = hgrepo[0].node().decode('ascii')

            timestamp = int(time.time())
            pushjs0 = PushJS(100, {
                'date': timestamp,
                'changesets': [rev0],
                'user': 'jdoe',
            })
            result = handlePushes(repo.pk, [pushjs0])

            with open(hgrepo.pathto('file.dtd'), 'w') as fh:
                fh.write('''
                <!ENTITY key1 "Hello">
                <!ENTITY key2 "Cruel">
                <!ENTITY key3 "World">
                ''')
            hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                          message="Second commit")
            rev1 = hgrepo[1].node().decode('ascii')

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
