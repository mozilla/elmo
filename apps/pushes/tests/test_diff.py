# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import re
import os
import logging
import codecs
import base64
from nose.tools import eq_, ok_
from django.core.urlresolvers import reverse
from django.conf import settings
from mercurial import commands as hgcommands
from mercurial.copies import pathcopies
from mercurial.hg import repository

from life.models import Repository
from .base import mock_ui, RepoTestBase
from pushes.views.diff import DiffView, BadRevision

# mercurial doesn't take unicode strings, trigger errors
import warnings
warnings.filterwarnings('error', category=UnicodeWarning)


class DiffTestCase(RepoTestBase):

    def setUp(self):
        super(DiffTestCase, self).setUp()
        self.repo_name = 'mozilla-central'
        self.repo = os.path.join(self._base, self.repo_name)

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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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
        """Test a diff across a different divergant clone"""
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

        self.dbrepo(name='orig', changesets_from=hgorig)
        self.dbrepo(name='clone', changesets_from=hgclone)
        # unit test part
        v = DiffView()
        v.getrepo('orig')
        files = v.contextsAndPaths(rev_from, rev_to, 'orig')
        eq_(files, [('file.dtd', 'changed')])
        lines = v.diffLines('file.dtd', 'changed')
        eq_(len(lines), 3)
        line = lines[0]
        eq_(line['class'], 'changed')
        eq_(line['entity'], 'mod')
        line = lines[1]
        eq_(line['class'], 'removed')
        eq_(line['entity'], 'new')
        line = lines[2]
        eq_(line['class'], 'added')
        eq_(line['entity'], 'new_in_clone')
        # integration test part, successful load and spot checks
        url = reverse('pushes:diff')
        # right now, we can't diff between repos, this might change!
        response = self.client.get(url, {'repo': 'clone',
                                         'from': rev_from[:12],
                                         'to': rev_to[:12]})
        eq_(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        ok_(re.findall('>\s*file\.dtd\s*<', html_diff))

    def test_diff_unrelated_repos(self):
        """Test for failure to diff unrelated repos"""
        ui = mock_ui()
        one = os.path.join(settings.REPOSITORY_BASE, 'one')
        other = os.path.join(settings.REPOSITORY_BASE, 'other')
        hgcommands.init(ui, one)
        hgone = repository(ui, one)
        (open(hgone.pathto('file.dtd'), 'w')
         .write('''
          <!ENTITY ent "val">
        '''))
        hgcommands.addremove(ui, hgone)
        hgcommands.commit(ui, hgone,
                          user="Jane Doe <jdoe@foo.tld",
                          message="initial commit")
        assert len(hgone) == 1  # 1 commit
        rev_from = hgone['tip'].hex()

        # different commit on other
        hgcommands.init(ui, other)
        hgother = repository(ui, other)
        (open(hgother.pathto('file.dtd'), 'w')
         .write('''
         <!ENTITY aunt "otherval">
         '''))
        hgcommands.addremove(ui, hgother)
        hgcommands.commit(ui, hgother,
                          user="John Doe <jodo@foo.tld",
                          message="a different commit on other")
        rev_to = hgother['tip'].hex()

        self.dbrepo(name='one', changesets_from=hgone)
        self.dbrepo(name='other', changesets_from=hgother)
        # unit test part
        v = DiffView()
        v.getrepo('one')
        with self.assertRaises(BadRevision) as badrev:
            v.contextsAndPaths(rev_from, rev_to, 'one')
        eq_(badrev.exception.args,
            ('from and to parameter are not connected',))
        # integration test part, failure to load
        url = reverse('pushes:diff')
        # right now, we can't diff between repos, this might change!
        response = self.client.get(url, {'repo': 'one',
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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

        url = reverse('pushes:diff')
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
        url = reverse('pushes:diff')

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


class ProcessForkTestCase(RepoTestBase):
    'Test that output of DiffView.processFork matches .status() and copies()'
    def setUp(self):
        # start with a single file with one entry
        super(ProcessForkTestCase, self).setUp()
        self.repo_name = 'mozilla-central'
        self.repo = os.path.join(self._base, self.repo_name)
        self.commit = self.edit = 0
        self.ui = mock_ui()
        hgcommands.init(self.ui, self.repo)
        self.hgrepo = repository(self.ui, self.repo)
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello %d">\n' % self.edit))
        (open(self.hgrepo.pathto('file2.dtd'), 'w')
             .write(u'<!ENTITY key1 "Goodbye">\n'))
        hgcommands.addremove(self.ui, self.hgrepo)
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="commit no: %d" % (self.commit))
        self.edit += 1
        self.commit += 1

    def _exec_test(self, ctx1, ctx2):
        r = self.hgrepo
        anc_rev = r[0].hex()
        repo = self.dbrepo()
        v = DiffView()
        v.getrepo(repo.name)
        logging.debug('orig files:\n%r', ctx1.manifest().keys())
        logging.debug('target files:\n%r', ctx2.manifest().keys())
        logging.debug('anc files:\n%r', r[0].manifest().keys())
        changed, added, removed, copies = v.processFork(r, ctx1, r, ctx2,
                                                        anc_rev)
        ref_changed, ref_added, ref_removed = r.status(ctx1, ctx2)[:3]
        logging.debug('hg changed, added, removed: %r',
                      (ref_changed, ref_added, ref_removed))
        eq_((changed, added, removed), (ref_changed, ref_added, ref_removed))
        eq_(copies, pathcopies(ctx1, ctx2))

    def test_same_file_change(self):
        rev0 = self.hgrepo[0].hex()
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_different_file_change(self):
        rev0 = self.hgrepo[0].hex()
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        (open(self.hgrepo.pathto('file2.dtd'), 'w')
             .write(u'<!ENTITY key1 "Goodbye Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_same_file_rename(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_same_file_rename_and_edit(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_different_rename(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('othernewnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_different_copy(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('othernewnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_different_copy_rename(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('othernewnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_different_rename_copy(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('othernewnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_edit_file_rename(self):
        rev0 = self.hgrepo[0].hex()
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_edit_file_copy(self):
        rev0 = self.hgrepo[0].hex()
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_edit_file_and_remove(self):
        rev0 = self.hgrepo[0].hex()
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.remove(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_remove_file_and_edit(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.remove(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        (open(self.hgrepo.pathto('file.dtd'), 'w')
             .write(u'<!ENTITY key1 "Hello Again">\n'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_remove_file_and_copy(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.remove(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_remove_file_and_rename(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.remove(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_rename_file_and_remove(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.rename(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'),
                          self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.remove(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)

    def test_copy_file_and_remove(self):
        rev0 = self.hgrepo[0].hex()
        hgcommands.copy(self.ui, self.hgrepo,
                        self.hgrepo.pathto('file.dtd'),
                        self.hgrepo.pathto('newnamefile.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="first commit")
        ctx1 = self.hgrepo['tip']
        hgcommands.update(self.ui, self.hgrepo, rev=rev0)
        hgcommands.remove(self.ui, self.hgrepo,
                          self.hgrepo.pathto('file.dtd'))
        hgcommands.commit(self.ui, self.hgrepo,
                  user="Jane Doe <jdoe@foo.tld>",
                  message="second commit")
        ctx2 = self.hgrepo['tip']
        self._exec_test(ctx1, ctx2)
