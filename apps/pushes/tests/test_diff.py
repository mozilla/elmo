# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import re
import os
import codecs
import base64
from django.core.urlresolvers import reverse
import hglib

from life.models import Repository
from .base import RepoTestBase, TestCase
from pushes.views.diff import DiffView

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertTrue(re.findall('>\s*file\.dtd\s*<', html_diff))
        self.assertIn('<tr class="line-added">', html_diff)
        self.assertTrue(re.findall('>\s*key3\s*<', html_diff))
        self.assertTrue(re.findall('>\s*World\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Cruel\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertTrue(re.findall('>\s*file\.dtd\s*<', html_diff))
        self.assertIn('<tr class="line-changed">', html_diff)
        self.assertIn(
            '<span class="equal">Cruel</span><span class="insert">le</span>',
            html_diff)

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertTrue(re.findall('>\s*file\.dtd\s*<', html_diff))
        self.assertIn('<tr class="line-removed">', html_diff)
        self.assertTrue(re.findall('>\s*key2\s*<', html_diff))
        self.assertTrue(re.findall('>\s*Cruel\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertTrue(re.findall('>\s*file2\.dtd\s*<', html_diff))
        self.assertIn('<tr class="line-added">', html_diff)
        self.assertTrue(re.findall('>\s*key9\s*<', html_diff))
        self.assertTrue(re.findall('>\s*Monde\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Hello\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertTrue(re.findall('>\s*file\.dtd\s*<', html_diff))
        # 2 entities with 2 rows each
        self.assertEqual(html_diff.count('<tr class="line-removed">'), 4)
        self.assertTrue(re.findall('>\s*key1\s*<', html_diff))
        self.assertTrue(re.findall('>\s*Hello\s*<', html_diff))
        self.assertTrue(re.findall('>\s*key2\s*<', html_diff))
        self.assertTrue(re.findall('>\s*Cruel\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertTrue(re.findall('>\s*file\.txt\s*<', html_diff))
        # 1 removed file
        self.assertEqual(html_diff.count('<div class="diff file-removed">'), 1)
        # also, expect a link to the old revision of the file
        change_ref = 'href="%sfile/%s/file.txt"' % (repo_url, rev0)
        self.assertIn(change_ref, html_diff)
        self.assertFalse(re.findall('>\s*line 1\s*<', html_diff))
        self.assertFalse(re.findall('>\s*line 2\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('renamed from file.dtd', re.sub('<.*?>', '', html_diff))
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Hello\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('renamed from file.txt', re.sub('<.*?>', '', html_diff))
        self.assertTrue(re.findall('>\s*newnamefile\.txt\s*<', html_diff))
        self.assertFalse(re.findall('>\s*line 1\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('renamed from file.dtd', re.sub('<.*?>', '', html_diff))
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Hello\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Cruel\s*<', html_diff))
        self.assertTrue(re.findall('>\s*World\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = (response.content
                     .split('Changed files:')[1]
                     .split('page_footer')[0])
        html_diff = unicode(html_diff, 'utf-8')
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertIn('Cannot parse file', html_diff)

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
        self.assertEqual(response.status_code, 200)
        html_diff = (response.content
                     .split('Changed files:')[1]
                     .split('page_footer')[0])
        html_diff = unicode(html_diff, 'utf-8')
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertIn('Cannot parse file', html_diff)
        self.assertEqual(html_diff.count('Cannot parse file'), 1)
        self.assertIn('renamed from file.dtd', re.sub('<.*?>', '', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = (response.content
                     .split('Changed files:')[1]
                     .split('page_footer')[0])
        html_diff = unicode(html_diff, 'utf-8')
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertIn('Cannot parse file', html_diff)
        self.assertEqual(html_diff.count('Cannot parse file'), 1)

    def test_error_handling(self):
        """Test various bad request parameters to the diff_app
        and assure that it responds with the right error codes."""
        hgrepo = hglib.init(self.repo).open()

        url = reverse('pushes:diff')
        response = self.client.get(url, {})
        self.assertEqual(response.status_code, 400)
        response = self.client.get(url, {'repo': 'junk'})
        self.assertEqual(response.status_code, 404)

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
        self.assertEqual(response.status_code, 400)

        # missing 'to'
        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': rev0
        })
        self.assertEqual(response.status_code, 400)

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('copied from file.dtd', re.sub('<.*?>', '', html_diff))
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Hello\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Cruel\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('copied from file.txt', re.sub('<.*?>', '', html_diff))
        self.assertTrue(re.findall('>\s*newnamefile\.txt\s*<', html_diff))
        self.assertFalse(re.findall('>\s*line 1\s*<', html_diff))
        self.assertFalse(re.findall('>\s*line 2\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('copied from file.dtd', re.sub('<.*?>', '', html_diff))
        self.assertTrue(re.findall('>\s*newnamefile\.dtd\s*<', html_diff))
        self.assertFalse(re.findall('>\s*Hello\s*<', html_diff))
        self.assertTrue(re.findall('>\s*Cruel\s*<', html_diff))
        self.assertTrue(re.findall('>\s*World\s*<', html_diff))

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('Cannot parse file', html_diff)
        # also, expect a link to this file
        change_ref = 'href="%sfile/%s/file.png"' % (repo_url, rev1)
        self.assertIn(change_ref, html_diff)

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('Cannot parse file', html_diff)
        # also, expect a link to this file
        change_url = repo_url + 'file/%s/file.dtd' % rev1
        self.assertIn('href="%s"' % change_url, html_diff)

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
        self.assertEqual(response.status_code, 200)
        html_diff = response.content.split('Changed files:')[1]
        self.assertIn('Cannot parse file', html_diff)
        # also, expect a link to this file
        change_url = repo_url + 'file/%s/file.dtd' % rev1
        self.assertIn('href="%s"' % change_url, html_diff)

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
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': 'xxx',
            'to': rev1
        })
        self.assertEqual(response.status_code, 400)

        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': rev0,
            'to': 'xxx'
        })
        self.assertEqual(response.status_code, 400)

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
        self.dbrepo(changesets_from=hgrepo)
        hgrepo.close()

        url = reverse('pushes:diff')

        # test forward, key removed
        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': rev0,
            'to': 'default'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertNotIn('line-added', response.content)

        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': rev0,
            'to': 'tip'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertNotIn('line-added', response.content)

        # test backward, key added
        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': 'default',
            'to': rev0
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('line-added', response.content)
        self.assertNotIn('line-removed', response.content)

        response = self.client.get(url, {
            'repo': self.repo_name,
            'from': 'tip',
            'to': rev0
        })
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 200)
        self.assertIn('line-removed', response.content)
        self.assertIn('line-added', response.content)


class ValuedDiffView(DiffView):
    '''Subclass to return a given list of contents.
    This utilizes the fact that keyword arguments in the default
    View constructor get set as attrs.'''
    def content(self, path, rev):
        if rev == self.rev1:
            return self.content1
        return self.content2


class TestDiffLines(TestCase):
    '''Unit test DiffView.diffLines'''

    def test_add_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'',
            content2=b'''key1 = My Value
    .attr = Attrbute
''',
        )
        lines = view.diffLines('file.ftl', 'added')
        self.assertEqual(len(lines), 1)
        val_line, = lines
        self.assertEqual(val_line['entity'], 'key1')
        self.assertEqual(val_line['class'], 'added')
        self.assertListEqual(
            [d['value'] for d in val_line['oldval']],
            [])
        self.assertListEqual(
            [d['class'] for d in val_line['oldval']],
            [])
        self.assertListEqual(
            [d['value'] for d in val_line['newval']],
            [u'My Value'])
        self.assertNotIn('class', val_line['newval'][0])

    def test_modify_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = My Value
    .attr = Attrbute
''',
            content2=b'''key1 = My New Value
    .attr = Attribute
''',
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertEqual(len(lines), 2)
        val_line, attr_line = lines
        self.assertEqual(val_line['entity'], 'key1')
        self.assertEqual(val_line['class'], 'changed')
        self.assertListEqual(
            [d['value'] for d in val_line['oldval']],
            [u'My', u' Value'])
        self.assertListEqual(
            [d['class'] for d in val_line['oldval']],
            [u'equal', u'equal'])
        self.assertListEqual(
            [d['value'] for d in val_line['newval']],
            [u'My', u' New', u' Value'])
        self.assertListEqual(
            [d['class'] for d in val_line['newval']],
            [u'equal', u'insert', u'equal'])
        self.assertEqual(attr_line['entity'], 'key1.attr')
        self.assertEqual(attr_line['class'], 'changed')
        self.assertListEqual(
            [d['value'] for d in attr_line['oldval']],
            [u'Attr', u'bute'])
        self.assertListEqual(
            [d['class'] for d in attr_line['oldval']],
            [u'equal', u'equal'])
        self.assertListEqual(
            [d['value'] for d in attr_line['newval']],
            [u'Attr', u'i', u'bute'])
        self.assertListEqual(
            [d['class'] for d in attr_line['newval']],
            [u'equal', u'insert', u'equal'])

    def test_copied_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = Old Value
''',
            content2=b'''key1 = New Value
''',
            copied={'file.ftl': 'orig.ftl'},
        )
        lines = view.diffLines('file.ftl', 'copied')
        self.assertListEqual(
            lines,
            [{'class': 'changed',
              'entity': u'key1',
              'newval': [{'class': 'replace', 'value': u'New'},
                         {'class': 'equal', 'value': u' Value'}],
              'oldval': [{'class': 'replace', 'value': u'Old'},
                         {'class': 'equal', 'value': u' Value'}]}]
            )

    def test_moved_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = Old Value
''',
            content2=b'''key1 = New Value
''',
            moved={'file.ftl': 'orig.ftl'},
        )
        lines = view.diffLines('file.ftl', 'moved')
        self.assertListEqual(
            lines,
            [{'class': 'changed',
              'entity': u'key1',
              'newval': [{'class': 'replace', 'value': u'New'},
                         {'class': 'equal', 'value': u' Value'}],
              'oldval': [{'class': 'replace', 'value': u'Old'},
                         {'class': 'equal', 'value': u' Value'}]}]
            )

    def test_removed_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = Old Value
''',
            content2=b'''key1 = New Value
''',
            moved={'file.ftl': 'orig.ftl'},
        )
        lines = view.diffLines('file.ftl', 'removed')
        self.assertListEqual(
            lines,
            [{'class': 'removed',
              'entity': u'key1',
              'newval': '',
              'oldval': [{'value': u'Old Value'}]}]
            )
