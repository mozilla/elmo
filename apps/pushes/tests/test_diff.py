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
import hglib

from life.models import Repository
from .base import RepoTestBase
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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            <!ENTITY key3 "World">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruelle">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file2.dtd'), 'w')
            .write('''
            <!ENTITY key9 "Monde">
            '''))
        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.remove(['path:file.dtd'])
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.txt'), 'w')
            .write('line 1\nline 2\n'))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.remove(['path:file.txt'])
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.move(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.txt'), 'w')
            .write('line 1\nline 2\n'))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.move(hgrepo.pathto('file.txt'),
                    hgrepo.pathto('newnamefile.txt'))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.move(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            <!ENTITY key3 "World">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.move(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        (codecs.open(hgrepo.pathto('newnamefile.dtd'), 'w', 'latin1')
            .write(u'''
            <!ENTITY key1 "Hell\xe2">
            <!ENTITY key2 "Cruel">
            <!ENTITY key3 "W\ex3rld">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
            .write(u'''
            <!ENTITY key1 "Hell\xe3">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.move(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "World">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
            .write(u'''
            <!ENTITY key1 "Hell\xe3">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.copy(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "World">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()

        url = reverse('pushes:diff')
        response = self.client.get(url, {})
        eq_(response.status_code, 400)
        response = self.client.get(url, {'repo': 'junk'})
        eq_(response.status_code, 404)

        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))
        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.copy(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()

        (open(hgrepo.pathto('file.txt'), 'w')
            .write('line 1\nline 2\n'))
        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.copy(hgrepo.pathto('file.txt'),
                    hgrepo.pathto('newnamefile.txt'))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        hgrepo.copy(hgrepo.pathto('file.dtd'),
                    hgrepo.pathto('newnamefile.dtd'))
        (open(hgrepo.pathto('newnamefile.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key3 "World">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.close()

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

    def test_diff_unrelated_repos(self):
        """Test for failure to diff unrelated repos"""
        one = os.path.join(settings.REPOSITORY_BASE, 'one')
        other = os.path.join(settings.REPOSITORY_BASE, 'other')
        hgone = hglib.init(one)
        hgone.open()
        (open(hgone.pathto('file.dtd'), 'w')
         .write('''
          <!ENTITY ent "val">
        '''))
        hgone.addremove()
        hgone.commit(user="Jane Doe <jdoe@foo.tld",
                     message="initial commit")
        assert hgone[0]  # 1 commit
        rev_from = hgone['tip'].node()

        # different commit on other
        hgother = hglib.init(other).open()
        (open(hgother.pathto('file.dtd'), 'w')
         .write('''
         <!ENTITY aunt "otherval">
         '''))
        hgother.addremove()
        hgother.commit(user="John Doe <jodo@foo.tld",
                       message="a different commit on other")
        rev_to = hgother['tip'].node()

        self.dbrepo(name='one', changesets_from=hgone)
        self.dbrepo(name='other', changesets_from=hgother)
        # unit test part
        v = DiffView()
        v.getrepo('one')
        with self.assertRaises(BadRevision) as badrev:
            v.contextsAndPaths(rev_from, rev_to)
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
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.png'), 'wb')
            .write(base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQAAAAA3bvkkAAAACklE'
                'QVR4nGNoAAAAggCBd81ytgAAAABJRU5ErkJggg=='
                )))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit",
                      addremove=True)
        rev0 = hgrepo[0].node()
        # a bit unfair of a change but works for the tests
        (open(hgrepo.pathto('file.png'), 'wb')
            .write(base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQAAAAA3bvkkAAAACklE'
                'QVR4nGNgAAAAAgABSK+kcQAAAABJRU5ErkJggg=='
                )))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()

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
        hgrepo = hglib.init(self.repo).open()

        # do this to trigger an exception on Mozilla.Parser.readContents
        _content = u'<!ENTITY key1 "Hell\xe3">\n'
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
               .write(_content))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit",
                      addremove=True)
        rev0 = hgrepo[0].node()

        (open(hgrepo.pathto('file.dtd'), 'w')
            .write(u'<!ENTITY key1 "Hello">\n'))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()

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
        hgrepo = hglib.init(self.repo).open()

        (open(hgrepo.pathto('file.dtd'), 'w')
            .write(u'<!ENTITY key1 "Hello">\n'))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit",
                      addremove=True)
        rev0 = hgrepo[0].node()

        # do this to trigger an exception on Mozilla.Parser.readContents
        _content = u'<!ENTITY key1 "Hell\xe3">\n'
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
            .write(_content))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()

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
        hgrepo = hglib.init(self.repo).open()

        (open(hgrepo.pathto('file.dtd'), 'w')
            .write(u'<!ENTITY key1 "Hello">\n'))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit",
                      addremove=True)
        rev0 = hgrepo[0].node()

        # do this to trigger an exception on Mozilla.Parser.readContents
        _content = u'<!ENTITY key1 "Hell\xe3">\n'
        (codecs.open(hgrepo.pathto('file.dtd'), 'w', 'latin1')
            .write(_content))

        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()

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

    def test_default_and_tip(self):
        """Test default and tip as from and to revision"""
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        dbrepo = self.dbrepo(changesets_from=hgrepo)
        hgrepo.close()

        url = reverse('pushes:diff')

        # test forward, key removed
        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': rev0,
            'to': 'default'
        })
        eq_(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertNotIn('line-added', response.content)

        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': rev0,
            'to': 'tip'
        })
        eq_(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertNotIn('line-added', response.content)

        # test backward, key added
        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': 'default',
            'to': rev0
        })
        eq_(response.status_code, 200)
        self.assertIn('line-added', response.content)
        self.assertNotIn('line-removed', response.content)

        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': 'tip',
            'to': rev0
        })
        eq_(response.status_code, 200)
        self.assertIn('line-added', response.content)
        self.assertNotIn('line-removed', response.content)

    def test_local_path_of_fork(self):
        """Test diffing a fork"""
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))

        hgrepo.addremove()
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit")
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        dbrepo = self.dbrepo(changesets_from=hgrepo)
        hgrepo.close()
        fork = self.dbrepo(name='fork')
        fork.fork_of = dbrepo
        fork.save()

        url = reverse('pushes:diff')

        # test forward, key removed
        response = self.client.get(url, {
            'repo': fork.name,
            'from': rev0,
            'to': rev1
        })
        eq_(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertNotIn('line-added', response.content)

    def test_local_path_of_divergent_fork(self):
        """Test diffing a fork with divergent commits"""
        hgrepo = hglib.init(self.repo).open()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            <!ENTITY key2 "Cruel">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="initial commit",
                      addremove=True)
        rev0 = hgrepo[0].node()
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key1 "Hello">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Second commit")
        rev1 = hgrepo[1].node()
        hgrepo.update(rev=rev0)
        (open(hgrepo.pathto('file.dtd'), 'w')
            .write('''
            <!ENTITY key2 "Cruel">
            '''))
        hgrepo.commit(user="Jane Doe <jdoe@foo.tld>",
                      message="Branch commit")
        rev2 = hgrepo[2].node()

        dbrepo = self.dbrepo(changesets_from=hgrepo, revrange=rev1)
        fork = self.dbrepo(name='fork', changesets_from=hgrepo,
                           revrange=rev2)
        fork.fork_of = dbrepo
        fork.save()
        hgrepo.close()

        url = reverse('pushes:diff')

        # test forward, key removed
        response = self.client.get(url, {
            'repo': fork.name,
            'from': rev1,
            'to': rev2
        })
        eq_(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertIn('line-added', response.content)
