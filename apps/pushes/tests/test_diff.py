# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import re
import codecs
from django.core.urlresolvers import reverse
import hglib

from life.models import Repository
from .base import RepoTestBase, TestCase
from pushes.views.diff import DataTree, DiffView, BadRevision

# mercurial doesn't take unicode strings, trigger errors
import warnings
warnings.filterwarnings('error', category=UnicodeWarning)


class DiffTestCase(RepoTestBase):

    repo_name = 'mozilla-central'

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


class TestPaths4Revs(RepoTestBase):

    repo_name = 'mozilla-central'

    def setUp(self):
        super(TestPaths4Revs, self).setUp()
        hgrepo = hglib.init(self.repo).open()
        # Initial commit, r=0
        with open(hgrepo.pathto('README'), 'w') as f:
            f.write('Initial commit')
        hgrepo.commit(user='Jane Doe <jdoe@foo.tld>',
                      message='Initial commit', addremove=True)
        # Add l10n file, r=1
        with open(hgrepo.pathto('f.ftl'), 'w') as f:
            f.write('message = text\n')
        hgrepo.commit(user='Jane Doe <jdoe@foo.tld>',
                      message='Adding file', addremove=True)
        # modify l10n file, r=2
        with open(hgrepo.pathto('f.ftl'), 'w') as f:
            f.write('message = othertext\n')
        hgrepo.commit(user='Jane Doe <jdoe@foo.tld>',
                      message='Modifying file', addremove=True)
        # copy and edit, r=3
        hgrepo.copy(hgrepo.pathto('f.ftl'), hgrepo.pathto('copied.ftl'))
        with open(hgrepo.pathto('copied.ftl'), 'w') as f:
            f.write('message = text\nnew_message = words\n')
        hgrepo.commit(user='Jane Doe <jdoe@foo.tld>',
                      message='Copying file', addremove=True)
        # move and edit, r=4
        hgrepo.move(hgrepo.pathto('f.ftl'), hgrepo.pathto('moved.ftl'))
        with open(hgrepo.pathto('moved.ftl'), 'w') as f:
            f.write('different = text\n')
        hgrepo.commit(user='Jane Doe <jdoe@foo.tld>',
                      message='Moving file', addremove=True)
        # remove, r=5
        hgrepo.remove([hgrepo.pathto('copied.ftl')])
        hgrepo.commit(user='Jane Doe <jdoe@foo.tld>',
                      message='Removing file', addremove=True)

    def test_repo_interactions(self):
        '''Let's just use a single test method for all our hg interactions,
        to reuse the hg repo fixture.
        '''
        dbrepo = self.dbrepo(changesets_from=hglib.open(self.repo))
        view = DiffView()
        view.getrepo(dbrepo.name)
        # add
        paths = view.paths4revs('0', '1')
        self.assertListEqual(
            paths,
            [('f.ftl', 'added')])
        self.assertDictEqual(view.moved, {})
        self.assertDictEqual(view.copied, {})
        # modified
        paths = view.paths4revs('1', '2')
        self.assertListEqual(
            paths,
            [('f.ftl', 'changed')])
        self.assertDictEqual(view.moved, {})
        self.assertDictEqual(view.copied, {})
        # copy
        paths = view.paths4revs('2', '3')
        self.assertListEqual(
            paths,
            [('copied.ftl', 'copied')])
        self.assertDictEqual(view.moved, {})
        self.assertDictEqual(
            view.copied,
            {'copied.ftl': 'f.ftl'})
        # move
        paths = view.paths4revs('3', '4')
        self.assertListEqual(
            paths,
            [('moved.ftl', 'moved')])
        self.assertDictEqual(
            view.moved,
            {'moved.ftl': 'f.ftl'})
        self.assertDictEqual(view.copied, {})
        # remove
        paths = view.paths4revs('4', '5')
        self.assertListEqual(
            paths,
            [('copied.ftl', 'removed')])
        self.assertDictEqual(view.moved, {})
        self.assertDictEqual(view.copied, {})

        # test tip and default (tip is default, not tip, really)
        self.assertEqual(view.real_rev('5'), view.real_rev('tip'))
        self.assertEqual(view.real_rev('5'), view.real_rev('default'))

        # test fork, just one of the code paths
        fork = self.dbrepo(name='fork')
        fork.fork_of = dbrepo
        fork.save()
        view.getrepo(fork.name)
        paths = view.paths4revs('0', '1')
        self.assertListEqual(
            paths,
            [('f.ftl', 'added')])
        self.assertDictEqual(view.moved, {})
        self.assertDictEqual(view.copied, {})

        # test revision lookup errors
        with self.assertRaises(BadRevision) as bad_rev_cm:
            view.paths4revs('iiii', '0')
        self.assertEqual(
            bad_rev_cm.exception.message,
            "Unrecognized 'from' parameter")
        with self.assertRaises(BadRevision) as bad_rev_cm:
            view.paths4revs('0', 'jjjj')
        self.assertEqual(
            bad_rev_cm.exception.message,
            "Unrecognized 'to' parameter")

        # test content retrieval from hg
        self.assertEqual(
            view.content('f.ftl', '1'),
            b'message = text\n')
        self.assertEqual(
            view.content('f.ftl', '2'),
            b'message = othertext\n')


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

    def test_broken_old_encoding(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=u'key1 = Hell\xe3'.encode('latin-1'),
            content2=b'key1 = My Value\n',
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertIsNone(lines)

    def test_broken_new_encoding(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'key1 = My Value\n',
            content2=u'key1 = Hell\xe3'.encode('latin-1'),
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertIsNone(lines)

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
        self.assertEqual(len(lines), 2)
        val_line, attr_line = lines
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
        self.assertEqual(attr_line['entity'], 'key1.attr')
        self.assertEqual(attr_line['class'], 'added')
        self.assertListEqual(
            [d['value'] for d in attr_line['oldval']],
            [])
        self.assertListEqual(
            [d['class'] for d in attr_line['oldval']],
            [])
        self.assertListEqual(
            [d['value'] for d in attr_line['newval']],
            [u'Attrbute'])
        self.assertNotIn('class', attr_line['newval'][0])

    def test_modify_fluent_add_val(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = My Value
''',
            content2=b'''key1 = My Value
key2 = Other
''',
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertListEqual(
            lines,
            [{'class': 'added',
              'entity': u'key2',
              'newval': [{'value': u'Other'}],
              'oldval': ''}])

    def test_modify_fluent_add_attr(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = My Value
''',
            content2=b'''key1 = My Value
key2
    .attr = Attr
''',
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertListEqual(
            lines,
            [{'class': 'added',
              'entity': u'key2.attr',
              'newval': [{'value': u'Attr'}],
              'oldval': ''}])

    def test_modify_fluent_val_attr(self):
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

    def test_modify_fluent_remove_val(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = My Value
key2 = Other
''',
            content2=b'''key1 = My Value
''',
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertListEqual(
            lines,
            [{'class': 'removed',
              'entity': u'key2',
              'oldval': [{'value': u'Other'}],
              'newval': ''}])

    def test_modify_fluent_remove_attr(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = My Value
key2
    .attr = Attr
''',
            content2=b'''key1 = My Value
''',
        )
        lines = view.diffLines('file.ftl', 'changed')
        self.assertListEqual(
            lines,
            [{'class': 'removed',
              'entity': u'key2.attr',
              'oldval': [{'value': u'Attr'}],
              'newval': ''}])

    def test_moved_to_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = Old Value
''',
            content2=b'''key1 = New Value
''',
            moved={'file.ftl': 'orig.foo'},
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

    def test_moved_to_non_fluent(self):
        view = ValuedDiffView(
            rev1='a',
            rev2='b',
            content1=b'''key1 = Old Value
''',
            content2=b'''key1 = New Value
''',
            moved={'file.foo': 'orig.ftl'},
        )
        lines = view.diffLines('file.foo', 'moved')
        self.assertIsNone(lines)


class TestTreeData(TestCase):

    def test_single(self):
        tree = DataTree(dict)
        tree['single/leaf'].update({'class': 'good'})
        view = DiffView()
        self.assertListEqual(
            view.tree_data(tree),
            [
                ('single/leaf', {'children': [], 'value': {'class': 'good'}}),
            ])

    def test_two_distinct(self):
        tree = DataTree(dict)
        tree['single/leaf'].update({'class': 'good'})
        tree['other/trunk'].update({'class': 'better'})
        view = DiffView()
        self.assertListEqual(
            view.tree_data(tree),
            [
                ('other/trunk', {'children': [],
                                 'value': {'class': 'better'}}),
                ('single/leaf', {'children': [], 'value': {'class': 'good'}}),
            ])

    def test_two_merge(self):
        tree = DataTree(dict)
        tree['single/leaf'].update({'class': 'good'})
        tree['single/trunk'].update({'class': 'better'})
        view = DiffView()
        self.assertListEqual(
            view.tree_data(tree),
            [
                ('single', {'children': [
                    ('leaf', {'children': [], 'value': {'class': 'good'}}),
                    ('trunk', {'children': [], 'value': {'class': 'better'}}),
                    ]}),
            ])
