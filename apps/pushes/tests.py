# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import os
import shutil
import tempfile
import codecs
import base64
import datetime
import time
try:
    import json
    json.dumps  # silence pyflakes
except:
    from django.utils import simplejson as json
from nose.tools import eq_, ok_
from test_utils import TestCase
from django import http
from django.core.urlresolvers import reverse
from django.conf import settings
from mercurial import commands as hgcommands
from mercurial.hg import repository
from mercurial.ui import ui as hg_ui
from mercurial.error import RepoError, RepoLookupError

from commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Repository, Push, Branch, File
from pushes import repo_fixtures
from pushes.utils import get_or_create_changeset
from pushes.views.api import jsonify
from pushes.utils import handlePushes, PushJS


class mock_ui(hg_ui):
    def write(self, *msg, **opts):
        pass


class PushesTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_push_log(self):
        """basic test rendering the pushlog"""
        url = reverse('pushes.views.pushlog')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        # like I said, a very basic test


class DiffTestCase(TestCase):

    def setUp(self):
        super(DiffTestCase, self).setUp()
        self._old_repository_base = getattr(settings, 'REPOSITORY_BASE', None)
        self._base = settings.REPOSITORY_BASE = tempfile.mkdtemp()
        self.repo_name = 'mozilla-central'
        self.repo = os.path.join(self._base, self.repo_name)

    def tearDown(self):
        super(DiffTestCase, self).tearDown()
        if os.path.isdir(self._base):
            shutil.rmtree(self._base)
        if self._old_repository_base is not None:
            settings.REPOSITORY_BASE = self._old_repository_base

    def test_file_entity_addition(self):
        """Change one file by adding a new line to it"""
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

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file\.dtd\s*<', html_diff))
        ok_('<tr class="line-added">' in html_diff)
        ok_(re.findall('>\s*key3\s*<', html_diff))
        ok_(re.findall('>\s*World\s*<', html_diff))
        ok_(not re.findall('>\s*Cruel\s*<', html_diff))

    def test_file_entity_modification(self):
        """Change one file by editing an existing line"""
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
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruelle">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file\.dtd\s*<', html_diff))
        ok_('<tr class="line-changed">' in html_diff)
        ok_('<span class="equal">Cruel</span><span class="insert">le</span>'
            in html_diff)

    def test_file_entity_removal(self):
        """Change one file by removal of a line"""
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
        (open(hgrepo.pathto('file.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file\.dtd\s*<', html_diff))
        ok_('<tr class="line-removed">' in html_diff)
        ok_(re.findall('>\s*key2\s*<', html_diff))
        ok_(re.findall('>\s*Cruel\s*<', html_diff))

    def test_new_file(self):
        """Change by adding a new second file"""
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
        (open(hgrepo.pathto('file2.dtd'), 'w')
             .write('''
             <!ENTITY key9 "Monde">
             '''))
        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file2\.dtd\s*<', html_diff))
        ok_('<tr class="line-added">' in html_diff)
        ok_(re.findall('>\s*key9\s*<', html_diff))
        ok_(re.findall('>\s*Monde\s*<', html_diff))
        ok_(not re.findall('>\s*Hello\s*<', html_diff))

    def test_remove_file(self):
        """Change by removing a file, with parser"""
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
        hgcommands.remove(ui, hgrepo, 'path:file.dtd')
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file\.dtd\s*<', html_diff))
        # 2 entities with 2 rows each
        eq_(html_diff.count('<tr class="line-removed">'), 4)
        ok_(re.findall('>\s*key1\s*<', html_diff))
        ok_(re.findall('>\s*Hello\s*<', html_diff))
        ok_(re.findall('>\s*key2\s*<', html_diff))
        ok_(re.findall('>\s*Cruel\s*<', html_diff))

    def test_remove_file_no_parser(self):
        """Change by removing a file, without parser"""
        ui = mock_ui()

        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.txt'), 'w')
             .write('line 1\nline 2\n'))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()
        hgcommands.remove(ui, hgrepo, 'path:file.txt')
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        repo_url = 'http://localhost:8001/%s/' % self.repo_name
        Repository.objects.create(
          name=self.repo_name,
          url=repo_url
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file\.txt\s*<', html_diff))
        # 1 removed file
        eq_(html_diff.count('<div class="diff file-removed">'), 1)
        # also, expect a link to the old revision of the file
        change_ref = 'href="%sfile/%s/file.txt"' % (repo_url, rev0)
        ok_(change_ref in html_diff)
        ok_(not re.findall('>\s*line 1\s*<', html_diff))
        ok_(not re.findall('>\s*line 2\s*<', html_diff))

    def test_file_only_renamed(self):
        """Change by doing a rename without any content editing"""
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

        hgcommands.rename(ui, hgrepo,
                          hgrepo.pathto('file.dtd'),
                          hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('renamed from file.dtd' in re.sub('<.*?>', '', html_diff))
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_(not re.findall('>\s*Hello\s*<', html_diff))

    def test_file_only_renamed_no_parser(self):
        """Change by doing a rename of a file without parser"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.txt'), 'w')
             .write('line 1\nline 2\n'))
        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        hgcommands.rename(ui, hgrepo,
                          hgrepo.pathto('file.txt'),
                          hgrepo.pathto('newnamefile.txt'))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('renamed from file.txt' in re.sub('<.*?>', '', html_diff))
        ok_(re.findall('>\s*newnamefile\.txt\s*<', html_diff))
        ok_(not re.findall('>\s*line 1\s*<', html_diff))

    def test_file_renamed_and_edited(self):
        """Change by doing a rename with content editing"""
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

        hgcommands.rename(ui, hgrepo,
                          hgrepo.pathto('file.dtd'),
                          hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "Cruel">
             <!ENTITY key3 "World">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('renamed from file.dtd' in re.sub('<.*?>', '', html_diff))
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_(not re.findall('>\s*Hello\s*<', html_diff))
        ok_(not re.findall('>\s*Cruel\s*<', html_diff))
        ok_(re.findall('>\s*World\s*<', html_diff))

    def test_file_renamed_and_edited_broken(self):
        """Change by doing a rename with bad content editing"""
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

        hgcommands.rename(ui, hgrepo,
                          hgrepo.pathto('file.dtd'),
                          hgrepo.pathto('newnamefile.dtd'))
        (codecs.open(hgrepo.pathto('newnamefile.dtd'), 'w', 'latin1')
             .write(u'''
             <!ENTITY key1 "Hell\xe2">
             <!ENTITY key2 "Cruel">
             <!ENTITY key3 "W\ex3rld">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = (response.content
                     .split('Changed files:')[1]
                     .split('page_footer')[0])
        html_diff = unicode(html_diff, 'utf-8')
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_('Cannot parse file' in html_diff)

    def test_file_renamed_and_edited_original_broken(self):
        """Change by doing a rename on a previously broken file"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)

        hgrepo = repository(ui, self.repo)
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
             .write(u'''
             <!ENTITY key1 "Hell\xe3">
             <!ENTITY key2 "Cruel">
             '''))
        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        hgcommands.rename(ui, hgrepo,
                          hgrepo.pathto('file.dtd'),
                          hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "World">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = (response.content
                     .split('Changed files:')[1]
                     .split('page_footer')[0])
        html_diff = unicode(html_diff, 'utf-8')
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_('Cannot parse file' in html_diff)
        eq_(html_diff.count('Cannot parse file'), 1)
        ok_('renamed from file.dtd' in re.sub('<.*?>', '', html_diff))

    def test_file_copied_and_edited_original_broken(self):
        """Change by copying a broken file"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)

        hgrepo = repository(ui, self.repo)
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
             .write(u'''
             <!ENTITY key1 "Hell\xe3">
             <!ENTITY key2 "Cruel">
             '''))
        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        hgcommands.copy(ui, hgrepo,
                        hgrepo.pathto('file.dtd'),
                        hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key2 "World">
             '''))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = (response.content
                     .split('Changed files:')[1]
                     .split('page_footer')[0])
        html_diff = unicode(html_diff, 'utf-8')
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_('Cannot parse file' in html_diff)
        eq_(html_diff.count('Cannot parse file'), 1)

    def test_error_handling(self):
        """Test various bad request parameters to the diff_app
        and assure that it responds with the right error codes."""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {})
        eq_(response.status_code, 400)
        response = self.client.get(url, {'repo': 'junk'})
        eq_(response.status_code, 404)

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

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        # missing 'from' and 'to'
        response = self.client.get(url, {'repo': self.repo_name})
        eq_(response.status_code, 400)

        # missing 'to'
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0
        })
        eq_(response.status_code, 400)

    def test_file_only_copied(self):
        """Change by copying a file with no content editing"""
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
        hgcommands.copy(ui, hgrepo,
                          hgrepo.pathto('file.dtd'),
                          hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('copied from file.dtd' in re.sub('<.*?>', '', html_diff))
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_(not re.findall('>\s*Hello\s*<', html_diff))
        ok_(not re.findall('>\s*Cruel\s*<', html_diff))

    def test_file_only_copied_no_parser(self):
        """Change by copying a file without parser"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)

        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.txt'), 'w')
             .write('line 1\nline 2\n'))
        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()
        hgcommands.copy(ui, hgrepo,
                          hgrepo.pathto('file.txt'),
                          hgrepo.pathto('newnamefile.txt'))
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('copied from file.txt' in re.sub('<.*?>', '', html_diff))
        ok_(re.findall('>\s*newnamefile\.txt\s*<', html_diff))
        ok_(not re.findall('>\s*line 1\s*<', html_diff))
        ok_(not re.findall('>\s*line 2\s*<', html_diff))

    def test_file_copied_and_edited(self):
        """Change by copying a file and then content editing"""
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
        hgcommands.copy(ui, hgrepo,
                          hgrepo.pathto('file.dtd'),
                          hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
             .write('''
             <!ENTITY key1 "Hello">
             <!ENTITY key3 "World">
             '''))

        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        Repository.objects.create(
          name=self.repo_name,
          url='http://localhost:8001/%s/' % self.repo_name
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('copied from file.dtd' in re.sub('<.*?>', '', html_diff))
        ok_(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        ok_(not re.findall('>\s*Hello\s*<', html_diff))
        ok_(re.findall('>\s*Cruel\s*<', html_diff))
        ok_(re.findall('>\s*World\s*<', html_diff))

    def test_diff_base_against_clone(self):
        """Test that the right error is raised on trying to do a diff across
        a different divergant clone"""
        ui = mock_ui()
        orig = os.path.join(settings.REPOSITORY_BASE, 'orig')
        clone = os.path.join(settings.REPOSITORY_BASE, 'clone')
        hgcommands.init(ui, orig)
        hgorig = repository(ui, orig)
        (open(hgorig.pathto('file.dtd'), 'w')
         .write('''
          <!ENTITY old "content we will delete">
          <!ENTITY mod "this has stuff to keep and delete">
        '''))
        hgcommands.addremove(ui, hgorig)
        hgcommands.commit(ui, hgorig,
                          user="Jane Doe <jdoe@foo.tld",
                          message="initial commit")
        assert len(hgorig) == 1  # 1 commit

        # set up a second repo called 'clone'
        hgcommands.clone(ui, orig, clone)
        hgclone = repository(ui, clone)

        # new commit on base
        (open(hgorig.pathto('file.dtd'), 'w')
         .write('''
         <!ENTITY mod "this has stuff to keep and add">
         <!ENTITY new "this has stuff that is new">
         '''))
        hgcommands.commit(ui, hgorig,
                          user="Jane Doe <jdoe@foo.tld",
                          message="second commit on base")
        assert len(hgorig) == 2  # 2 commits
        rev_from = hgorig[1].hex()

        # different commit on clone
        (open(hgclone.pathto('file.dtd'), 'w')
         .write('''
         <!ENTITY mod "this has stuff to keep and change">
         <!ENTITY new_in_clone "this has stuff that is different from base">
         '''))
        hgcommands.commit(ui, hgclone,
                          user="John Doe <jodo@foo.tld",
                          message="a different commit on clone")
        rev_to = hgclone[1].hex()

        Repository.objects.create(
          name='orig',
          url='http://localhost:8001/orig/'
        )
        Repository.objects.create(
          name='clone',
          url='http://localhost:8001/clone/'
        )

        url = reverse('pushes.views.diff')
        # right now, we can't diff between repos, this might change!
        response = self.client.get(url, {'repo': 'clone',
                                         'from': rev_from[:12],
                                         'to': rev_to[:12]})
        eq_(response.status_code, 400)

    def test_binary_file_edited(self):
        """Modify a binary file"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)
        (open(hgrepo.pathto('file.png'), 'wb')
             .write(base64.b64decode(
                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQAAAAA3bvkkAAAACklE'
                 'QVR4nGNoAAAAggCBd81ytgAAAABJRU5ErkJggg=='
                 )))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()
        # a bit unfair of a change but works for the tests
        (open(hgrepo.pathto('file.png'), 'wb')
             .write(base64.b64decode(
                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQAAAAA3bvkkAAAACklE'
                 'QVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg=='
                 )))

        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        repo_url = 'http://localhost:8001/' + self.repo_name + '/'
        Repository.objects.create(
          name=self.repo_name,
          url=repo_url
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('Cannot parse file' in html_diff)
        # also, expect a link to this file
        change_ref = 'href="%sfile/%s/file.png"' % (repo_url, rev1)
        ok_(change_ref in html_diff)

    def test_broken_encoding_file_add(self):
        """Change by editing an already broken file"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)

        # do this to trigger an exception on Mozilla.Parser.readContents
        _content = u'<!ENTITY key1 "Hell\xe3">\n'
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
          .write(_content))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        (open(hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello">\n'))

        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        repo_url = 'http://localhost:8001/' + self.repo_name + '/'
        Repository.objects.create(
          name=self.repo_name,
          url=repo_url
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('Cannot parse file' in html_diff)
        # also, expect a link to this file
        change_url = repo_url + 'file/%s/file.dtd' % rev1
        ok_('href="%s"' % change_url in html_diff)

    def test_file_edited_broken_encoding(self):
        """Change by editing a good with a broken edit"""
        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)

        (open(hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello">\n'))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        # do this to trigger an exception on Mozilla.Parser.readContents
        _content = u'<!ENTITY key1 "Hell\xe3">\n'
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
          .write(_content))

        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        repo_url = 'http://localhost:8001/' + self.repo_name + '/'
        Repository.objects.create(
          name=self.repo_name,
          url=repo_url
        )

        url = reverse('pushes.views.diff')
        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_('Cannot parse file' in html_diff)
        # also, expect a link to this file
        change_url = repo_url + 'file/%s/file.dtd' % rev1
        ok_('href="%s"' % change_url in html_diff)

    def test_bogus_repo_hashes(self):
        """test to satisfy
        https://bugzilla.mozilla.org/show_bug.cgi?id=750533
        which says that passing unrecognized repo hashes
        should yield a 400 Bad Request error.
        """
        ui = mock_ui()
        hgcommands.init(ui, self.repo)
        hgrepo = repository(ui, self.repo)

        (open(hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello">\n'))

        hgcommands.addremove(ui, hgrepo)
        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="initial commit")
        rev0 = hgrepo[0].hex()

        # do this to trigger an exception on Mozilla.Parser.readContents
        _content = u'<!ENTITY key1 "Hell\xe3">\n'
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
          .write(_content))

        hgcommands.commit(ui, hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="Second commit")
        rev1 = hgrepo[1].hex()

        repo_url = 'http://localhost:8001/' + self.repo_name + '/'
        Repository.objects.create(
          name=self.repo_name,
          url=repo_url
        )
        url = reverse('pushes.views.diff')

        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': rev1
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': 'xxx',
          'to': rev1
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
          'repo': self.repo_name,
          'from': rev0,
          'to': 'xxx'
        })
        eq_(response.status_code, 400)


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


class ApiTestCase(TestCase):

    def setUp(self):
        super(ApiTestCase, self).setUp()
        self._old_repository_base = getattr(settings, 'REPOSITORY_BASE', None)
        self._base = settings.REPOSITORY_BASE = tempfile.mkdtemp()
        self.repo_data = repo_fixtures.network(self._base)
        for name, hgrepo in self.repo_data['repos'].iteritems():
            dbrepo = Repository.objects.create(
                name=name,
                url='http://localhost:8001/%s/' % name
            )
            for i in hgrepo:
                get_or_create_changeset(dbrepo, hgrepo, hgrepo[i].hex())

    def tearDown(self):
        super(ApiTestCase, self).tearDown()
        if os.path.isdir(self._base):
            shutil.rmtree(self._base)
        if self._old_repository_base is not None:
            settings.REPOSITORY_BASE = self._old_repository_base

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


class TestHandlePushes(TestCase):

    def setUp(self):  # copied from DiffTestCase
        super(TestHandlePushes, self).setUp()
        self._old_repository_base = getattr(settings, 'REPOSITORY_BASE', None)
        self._base = settings.REPOSITORY_BASE = tempfile.mkdtemp()
        self.repo_name = 'mozilla-central-original'
        self.repo = os.path.join(self._base, self.repo_name)

    def tearDown(self):  # copied from DiffTestCase
        super(TestHandlePushes, self).tearDown()
        if os.path.isdir(self._base):
            shutil.rmtree(self._base)
        if self._old_repository_base is not None:
            settings.REPOSITORY_BASE = self._old_repository_base

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
