# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from importlib import import_module
import re
import os
from elmo.test import TestCase
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.conf import settings
from django.utils.encoding import force_text
from django.test import override_settings
from django.test.client import RequestFactory
import six.moves.urllib.parse
from six.moves import range
from life.models import Locale, TeamLocaleThrough
from elmo_commons.tests.mixins import EmbedsTestCaseMixin


def _local_feed_url(filename):
    filepath = os.path.join(os.path.dirname(__file__), filename)
    return 'file://' + filepath


# side-step whatever authentication backend has been set up otherwise
# we might end up trying to go online for some sort of LDAP lookup
@override_settings(AUTHENTICATION_BACKENDS=(
    'django.contrib.auth.backends.ModelBackend',
))
class HomepageTestCase(TestCase, EmbedsTestCaseMixin):

    @override_settings(COMPRESS_DEBUG_TOGGLE='no-compression')
    def test_handler500(self):
        # The reason for doing this COMPRESS_DEBUG_TOGGLE "hack" is because
        # our 500.html extends "base.html" which uses ``compress`` blocks.
        # A way of switching that off entirely is to set COMPRESS_DEBUG_TOGGLE
        # and then match that with a GET variable with the same value.
        # That does the same as running django_compressor in offline mode
        # which is to basically do nothing and assume the compressed file just
        # exists.

        # import the root urlconf like django does when it starts up
        root_urlconf = import_module(settings.ROOT_URLCONF)
        # ...so that we can access the 'handler500' defined in there
        par, end = root_urlconf.handler500.rsplit('.', 1)
        # ...which is an importable reference to the
        # real handler500 function
        views = import_module(par)
        # ...and finally we the handler500 function at hand
        handler500 = getattr(views, end)

        # to make a mock call to the django view functions
        # you need a request
        fake_request = (RequestFactory()
                        .get('/', {'no-compression': 'true'}))

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an
        # exception has been raised which means sys.exc_info()
        # is something.
        try:
            raise NameError("sloppy code!")
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            self.assertEqual(response.status_code, 500)
            content = force_text(response.content)
            self.assertIn('Oops', content)

    # SESSION_COOKIE_SECURE has to be True for tests to work.
    # The reason this might be switched off is if you have set it to False
    # in your settings/local.py so you can use http://localhost:8000/
    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_secure_session_cookies(self):
        """secure session cookies should always be 'secure' and 'httponly'"""
        url = reverse('login')
        # run it as a mocked AJAX request because that's how elmo does it
        response = self.client.post(
            url,
            {'username': 'peterbe',
             'password': 'secret'},
            **{'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn('class="error', content)

        from django.contrib.auth.models import User
        user = User.objects.create(username='peterbe',
                                   first_name='Peter')
        user.set_password('secret')
        user.save()

        response = self.client.post(
            url,
            {'username': 'peterbe',
             'password': 'secret',
             'next': '/foo'},
            **{'X-Requested-With': 'XMLHttpRequest'})
        # even though it's
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith('/foo'))

        # if this fails it's because settings.SESSION_COOKIE_SECURE
        # isn't true
        assert settings.SESSION_COOKIE_SECURE
        self.assertTrue(self.client.cookies['sessionid']['secure'])

        # if this fails it's because settings.SESSION_COOKIE_HTTPONLY
        # isn't true
        assert settings.SESSION_COOKIE_HTTPONLY
        self.assertTrue(self.client.cookies['sessionid']['httponly'])

        # should now be logged in
        url = reverse('user-json')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        # "Hi Peter" or something like that
        self.assertIn('Peter', content)

    def test_index_page(self):
        """load the current homepage index view"""
        url = reverse('homepage')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)

    @override_settings(L10N_FEED_URL=_local_feed_url('test_rss20.xml'))
    def test_index_page_feed_reader(self):
        # clear the cache of the empty feed we have for other tests
        cache.clear()
        url = reverse('homepage')
        try:
            response = self.client.get(url)
        finally:
            cache.clear()
        self.assertEqual(response.status_code, 200)

        content = response.content
        if isinstance(content, six.binary_type):
            content = content.decode('utf-8')

        # because I know what's in test_rss20.xml I can
        # check for it here
        import feedparser
        assert settings.L10N_FEED_URL.startswith('file:///')
        parsed = feedparser.parse(settings.L10N_FEED_URL)
        entries = list(parsed.entries)
        first = entries[0]

        # because the titles are truncated in the template
        # we need to do the same here
        from django.template.defaultfilters import truncatewords
        self.assertIn(truncatewords(first['title'], 8), content)
        self.assertIn('href="%s"' % first['link'], content)

        second = parsed.entries[1]
        self.assertIn(truncatewords(second['title'], 8), content)
        self.assertIn('href="%s"' % second['link'], content)

    def test_teams_page(self):
        """check that the teams page renders correctly"""
        Locale.objects.create(
          code='en-US',
          name=None,
        )
        Locale.objects.create(
          code='fr',
          name='French',
        )
        Locale.objects.create(
          code='sv-SE',
          name='Swedish',
        )
        Locale.objects.create(
          code='br-BR',
          name=None,
        )

        url = reverse('teams')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)
        content = force_text(response.content)
        content = content.split('id="teams"')[1]
        content = content.split('<footer')[0]

        url_fr = reverse('l10n-team', args=['fr'])
        url_sv = reverse('l10n-team', args=['sv-SE'])
        url_br = reverse('l10n-team', args=['br-BR'])
        self.assertIn(url_fr, content)
        self.assertIn(url_sv, content)
        self.assertIn(url_br, content)
        url_en = reverse('l10n-team', args=['en-US'])
        self.assertNotIn(url_en, content)
        self.assertTrue(
            -1 < content.find('br-BR')
               < content.find('French')
               < content.find('Swedish'))
        self.assertNotIn('en-US', content)

    def test_teams_page_with_team_locales_hidden(self):
        """locales that are owned by another team
        should not appear on the teams page."""
        sr_latn = Locale.objects.create(
          code='sr-Latn',
          name=None,
        )
        sr = Locale.objects.create(
          code='sr',
          name='Serbian',
        )
        team_locale = TeamLocaleThrough.objects.create(
          team=sr,
          locale=sr_latn
        )

        url = reverse('teams')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        content = content.split('id="teams"')[1]
        content = content.split('<footer')[0]

        url_sr = reverse('l10n-team', args=['sr'])
        url_sr_latn = reverse('l10n-team', args=['sr-Latn'])
        self.assertIn(url_sr, content)
        self.assertNotIn(url_sr_latn, content)

        today = datetime.datetime.utcnow()
        tomorrow = today + datetime.timedelta(days=1)
        team_locale.start = tomorrow
        team_locale.save()
        response = self.client.get(url)
        content = force_text(response.content)
        self.assertIn(url_sr, content)
        self.assertIn(url_sr_latn, content)

        yesterday = today - datetime.timedelta(days=1)
        team_locale.start = None
        team_locale.end = yesterday
        team_locale.save()
        response = self.client.get(url)
        content = force_text(response.content)
        self.assertIn(url_sr, content)
        self.assertIn(url_sr_latn, content)

        team_locale.start = yesterday
        team_locale.end = tomorrow
        team_locale.save()
        response = self.client.get(url)
        content = force_text(response.content)
        self.assertIn(url_sr, content)
        self.assertNotIn(url_sr_latn, content)

    def test_team_page_with_owning_team(self):
        """Trying to reach a locale owned by another team should redirect. """
        sr_latn = Locale.objects.create(
          code='sr-Latn',
          name=None,
        )
        sr = Locale.objects.create(
          code='sr',
          name='Serbian',
        )
        team_locale = TeamLocaleThrough.objects.create(
          team=sr,
          locale=sr_latn
        )

        url_sr = reverse('l10n-team', args=['sr'])
        url_sr_latn = reverse('l10n-team', args=['sr-Latn'])

        response = self.client.get(url_sr_latn)
        self.assertRedirects(response, url_sr)

        # and if the start and end date are "out of window"...
        today = datetime.datetime.utcnow()
        tomorrow = today + datetime.timedelta(days=1)
        team_locale.start = tomorrow
        team_locale.save()
        response = self.client.get(url_sr_latn)
        self.assertEqual(response.status_code, 200)

        yesterday = today - datetime.timedelta(days=1)
        team_locale.start = None
        team_locale.end = yesterday
        team_locale.save()
        response = self.client.get(url_sr_latn)
        self.assertEqual(response.status_code, 200)

        team_locale.start = yesterday
        team_locale.end = tomorrow
        team_locale.save()
        response = self.client.get(url_sr_latn)
        self.assertRedirects(response, url_sr)

    def test_team_page(self):
        """test a team (aka. locale) page"""
        Locale.objects.create(
          code='sv-SE',
          name='Swedish',
        )
        url = reverse('l10n-team', args=['xxx'])
        response = self.client.get(url)
        # XXX would love for this to be a 404 instead (peterbe)
        self.assertEqual(response.status_code, 302)
        url = reverse('l10n-team', args=['sv-SE'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assert_all_embeds(content)
        self.assertIn('Swedish', content)
        # it should also say "Swedish" in the <h1>
        h1_text = re.findall('<h1[^>]*>(.*?)</h1>',
                             content,
                             re.M | re.DOTALL)[0]
        self.assertIn('Swedish', h1_text)

    def test_pushes_redirect(self):
        """test if the old /pushes url redirects to /source/pushes"""
        old_response = self.client.get('/pushes/repo?path=query')
        self.assertEqual(old_response.status_code, 301)
        target_url = reverse('pushes:pushlog',
                             kwargs={'repo_name': 'repo'})
        new_response = self.client.get(target_url, {'path': 'query'})
        self.assertEqual(new_response.status_code, 200)
        self.assertEqual(
            six.moves.urllib.parse.urlparse(old_response['Location'])[2:],
            ('/source/pushes/repo', '', 'path=query', ''))

    def test_diff_redirect(self):
        """test if the old /pushes url redirects to /source/pushes"""
        diff_url = ('/shipping/diff?to=62f87d2952f4&from=fc700f4da954' +
                    '&tree=fx_beta&repo=some_repo&url=&locale=')
        old_response = self.client.get(diff_url)
        self.assertEqual(old_response.status_code, 301)
        target_url = reverse('pushes:diff')
        # not testing response, as we don't have a repo to back this up
        opath, oparam, oquery, ohash = \
            six.moves.urllib.parse.urlparse(old_response['Location'])[2:]
        self.assertEqual(
            (opath, oparam),
            six.moves.urllib.parse.urlparse(target_url)[2:4]
        )
        self.assertEqual(
            six.moves.urllib.parse.parse_qs(oquery),
            {
                'to': ['62f87d2952f4'],
                'from': ['fc700f4da954'],
                'tree': ['fx_beta'],
                'repo': ['some_repo']})

    def test_get_homepage_etag(self):
        arabic = Locale.objects.create(code='ar', name='Arabic')
        for i in range(1, 40 + 1):
            Locale.objects.create(
              name='Language-%d' % i,
              code='L%d' % i
            )
        url = reverse('homepage')
        response = self.client.get(url)
        assert response['ETag']
        etag_first = response['ETag']

        response = self.client.get(url)
        assert response['ETag']
        etag_second = response['ETag']
        self.assertEqual(etag_first, etag_second)

        # Edit an existing locale
        arabic.name = arabic.name.upper()
        arabic.save()

        response = self.client.get(url)
        self.assertTrue(response['ETag'])
        etag_third = response['ETag']
        self.assertNotEqual(etag_second, etag_third)
