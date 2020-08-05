# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import tempfile
from unittest import mock

import hglib

from pushes.tests.base import RepoTestBase
from elmo_queues import consumers
from life.models import Changeset, File, Forest, Repository


@mock.patch('elmo_queues.consumers.logging', mock.MagicMock())
@mock.patch('pushes.utils.logging', mock.MagicMock())
class TestHandleRepo(RepoTestBase):

    repo_name = 'releases/l10n/de'

    def setUp(self):
        super(TestHandleRepo, self).setUp()
        self.upstream = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.upstream):
            shutil.rmtree(self.upstream)
        super(TestHandleRepo, self).tearDown()

    def _repo(self):
        upstream = os.path.join(self.upstream, self.repo_name)
        os.makedirs(os.path.dirname(upstream))
        return upstream, hglib.init(upstream)

    def _forest(self):
        'Helper to create an upstream Forest db entry.'
        name = self.repo_name.rsplit('/', 1)[0]
        return Forest.objects.create(
            name=name,
            url=f'file://{self.upstream}/{name}/'
        )

    def test_not_elmo(self):
        ec = consumers.ElmoConsumer(None)
        ec.on_hg_newrepo('releases/l10n/de', {
            'data': {'repo_url': f'file://{self.upstream}/{self.repo_name}/'}
        })
        self.assertEqual(Changeset.objects.count(), 1)
        self.assertEqual(Repository.objects.count(), 0)

    def test_empty_upstream(self):
        upstream, _ = self._repo()
        self.assertTrue(os.path.isdir(os.path.join(upstream, '.hg')))
        self._forest()
        ec = consumers.ElmoConsumer(None)
        ec.on_hg_newrepo('releases/l10n/de', {
            'data': {'repo_url': f'file://{self.upstream}/{self.repo_name}/'}
        })
        self.assertEqual(Changeset.objects.count(), 1)
        self.assertListEqual(
            [r.name for r in Repository.objects.all()], [self.repo_name]
        )

    def test_existing_upstream(self):
        upstream, repo = self._repo()
        self.assertTrue(os.path.isdir(os.path.join(upstream, '.hg')))
        with repo:
            for f in ('f1', 'f2'):
                repo.update(rev=12*'0')
                fname = os.path.join(upstream, f)
                with open(fname, 'w', encoding='utf-8') as fh:
                    fh.write(f)
                repo.commit(
                    message=f'Adding {f}',
                    user="Jane Doe <jdoe@foo.tld>",
                    addremove=True,
                )
        self._forest()
        ec = consumers.ElmoConsumer(None)
        ec.on_hg_newrepo('releases/l10n/de', {
            'data': {'repo_url': f'file://{self.upstream}/{self.repo_name}/'}
        })
        self.assertEqual(Changeset.objects.count(), 3)
        self.assertListEqual(
            [r.name for r in Repository.objects.all()], [self.repo_name]
        )
        self.assertListEqual(
            sorted((f.path for f in File.objects.all())),
            ['f1', 'f2']
        )
