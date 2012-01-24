# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Peter Bengtsson <peterbe@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import re
import os
import shutil
import tempfile
import codecs
import base64
try:
    import json
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
from mercurial.error import RepoError

from commons.tests.mixins import EmbedsTestCaseMixin
from life.models import Repository
from pushes import repo_fixtures
from pushes.utils import getChangeset
from pushes.views.api import jsonify


class PushesTestCase(TestCase, EmbedsTestCaseMixin):

    def test_render_push_log(self):
        """basic test rendering the pushlog"""
        url = reverse('pushes.views.pushlog')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        # like I said, a very basic test


class DiffTestCase(TestCase):

    class _ui(hg_ui):
        def write(self, *msg, **opts):
            pass

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
        ui = self._ui()

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
        ui = self._ui()

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
        ui = self._ui()

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
        ui = self._ui()

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
        ui = self._ui()

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
        ui = self._ui()

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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
        self.assertRaises(RepoError, self.client.get,
                          url, {'repo': 'clone',
                                'from': rev_from[:12],
                                'to': rev_to[:12]})

    def test_binary_file_edited(self):
        """Modify a binary file"""
        ui = self._ui()
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
        ui = self._ui()
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
        ui = self._ui()
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
                getChangeset(dbrepo, hgrepo, hgrepo[i].hex())

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
