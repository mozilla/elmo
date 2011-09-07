from django.test import TestCase
from nose.tools import eq_, ok_, raises
import os.path
import shutil
import tempfile
from mercurial import commands as hgcommands
from mercurial.hg import repository
from mercurial.ui import ui as _ui
from mercurial.error import RepoError

from django.conf import settings
from django.core.urlresolvers import reverse

from life.models import Repository, Changeset
from pushes.utils import getChangeset
from commons.tests.mixins import EmbedsTestCaseMixin

_BASE_BACKUP = None


def setUpModule():
    """Create some fake repositories, we'll need that"""
    _BASE_BACKUP = settings.REPOSITORY_BASE
    base = settings.REPOSITORY_BASE = tempfile.mkdtemp()
    ui = _ui()
    hgcommands.init(ui, os.path.join(base, 'orig'))
    hgorig = repository(ui, os.path.join(base, 'orig'))
    # start off with a base commit
    (open(hgorig.pathto('file.dtd'), 'w')
     .write('''
<!ENTITY old "content we will delete">
<!ENTITY mod "this has stuff to keep and delete">
'''))
    hgcommands.addremove(ui, hgorig)
    hgcommands.commit(ui, hgorig,
                      user="Jane Doe <jdoe@foo.tld",
                      message="initial commit")
    hgcommands.clone(ui, os.path.join(base, 'orig'),
                     os.path.join(base, 'clone'))
    hgclone = repository(ui, os.path.join(base, 'clone'))
    # new commit on base
    (open(hgorig.pathto('file.dtd'), 'w')
     .write('''
<!ENTITY mod "this has stuff to keep and add">
<!ENTITY new "this has stuff that is new">
'''))
    hgcommands.commit(ui, hgorig,
                      user="Jane Doe <jdoe@foo.tld",
                      message="second commit on base")
    # different commit on clone
    (open(hgclone.pathto('file.dtd'), 'w')
     .write('''
<!ENTITY mod "this has stuff to keep and change">
<!ENTITY new_in_clone "this has stuff that is different from base">
'''))
    hgcommands.commit(ui, hgclone,
                      user="John Doe <jodo@foo.tld",
                      message="a different commit on clone")
    # and now something completely different
    hgcommands.init(ui, os.path.join(base, 'indie'))
    hgindie = repository(ui, os.path.join(base, 'indie'))
    (open(hgindie.pathto('file.dtd'), 'w')
     .write('''
<!ENTITY mod "this has stuff to keep and do independently">
<!ENTITY indie "this has stuff that is nowhere else">
'''))
    hgcommands.addremove(ui, hgindie)
    hgcommands.commit(ui, hgindie,
                      user="Joe Black <jblack@foo.tld",
                      message="initial commit on indie repo")


def tearDownModule():
    """Delete the fake repositories"""
    try:
        shutil.rmtree(settings.REPOSITORY_BASE)
    except OSError:
        # we probably failed to create the repo base in the first place,
        # don't fail now
        pass
    settings.REPOSITORY_BASE = _BASE_BACKUP


class RepoTest(TestCase, EmbedsTestCaseMixin):
    def setUp(self):
        self.orig = (Repository.objects
                     .create(name='orig',
                              url='http://localhost:8001/orig/'))
        self.clone = (Repository.objects
                      .create(name='clone',
                               url='http://localhost:8001/clone/'))
        self.indie = (Repository.objects
                      .create(name='indie',
                               url='http://localhost:8001/indie/'))
        # now load the changesets etc into the db from disk
        for reponame in ('orig', 'clone', 'indie'):
            dbrepo = getattr(self, reponame)
            hgrepo = repository(_ui(), os.path.join(settings.REPOSITORY_BASE,
                                                     reponame))
            for i in hgrepo:
                getChangeset(dbrepo, hgrepo, hgrepo[i].hex())

    def test_setUp(self):
        eq_(Changeset.objects.order_by('id')[0].revision,
            40 * '0')
        eq_(Changeset.objects.count(), 5)

    def test_diff_content(self):
        to_, from_ = (self.orig
                      .changesets.order_by('-pk')
                      .values_list('revision', flat=True)[:2])
        url = reverse('shipping.views.diff_app')
        response = self.client.get(url, {'repo': self.orig.name,
                                          'from': from_[:12],
                                          'to': to_[:12]})
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('<tr class="line-removed">' in response.content)
        ok_('<tr class="line-changed">' in response.content)
        ok_('<tr class="line-added">' in response.content)
        ok_('<span class="equal">' in response.content)
        ok_('<span class="replace">' in response.content)

    def test_diff_within_orig(self):
        to_, from_ = (self.orig
                      .changesets.order_by('-pk')
                      .values_list('revision', flat=True)[:2])
        url = reverse('shipping.views.diff_app')
        response = self.client.get(url, {'repo': self.orig.name,
                                          'from': from_[:12],
                                          'to': to_[:12]})
        eq_(response.status_code, 200)

    def test_diff_within_clone(self):
        to_, from_ = (self.clone
                      .changesets.order_by('-pk')
                      .values_list('revision', flat=True)[:2])
        url = reverse('shipping.views.diff_app')
        response = self.client.get(url, {'repo': self.clone.name,
                                          'from': from_[:12],
                                          'to': to_[:12]})
        eq_(response.status_code, 200)

    def test_diff_base_against_clone(self):
        from_ = self.orig.changesets.order_by('-pk')[0].shortrev
        to_ = self.clone.changesets.order_by('-pk')[0].shortrev
        url = reverse('shipping.views.diff_app')
        # FIXME: right now, we can't diff between repos, so this
        self.assertRaises(RepoError, self.client.get,
                          url, {'repo': self.clone.name,
                                 'from': from_[:12],
                                 'to': to_[:12]})
        #eq_(response.status_code, 200)
