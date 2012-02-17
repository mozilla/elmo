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
# Portions created by the Initial Developer are Copyright (C) 2010
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
from mock import patch
from test_utils import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import Http404
from django.test.client import RequestFactory
from django.core.urlresolvers import Resolver404
from nose.tools import eq_, ok_
from life.models import Locale
from commons.tests.mixins import EmbedsTestCaseMixin
import urlparse


class HomepageTestCase(TestCase, EmbedsTestCaseMixin):

    def setUp(self):
        super(HomepageTestCase, self).setUp()

        # SESSION_COOKIE_SECURE has to be True for tests to work.
        # The reason this might be switched off is if you have set it to False
        # in your settings/local.py so you can use http://localhost:8000/
        settings.SESSION_COOKIE_SECURE = True

        # side-step whatever authentication backend has been set up otherwise
        # we might end up trying to go online for some sort of LDAP lookup
        self._original_auth_backends = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (
          'django.contrib.auth.backends.ModelBackend',
        )

        # make sure this is always set to something and iff the mocking of
        # django_arecibo was to fail at least it won't send anything to a real
        # arecibo server
        settings.ARECIBO_SERVER_URL = 'http://arecibo/'

        settings.L10N_FEED_URL = self._local_feed_url('test_rss20.xml')

    def _local_feed_url(self, filename):
        filepath = os.path.join(os.path.dirname(__file__), filename)
        return 'file://' + filepath

    def tearDown(self):
        super(HomepageTestCase, self).tearDown()
        settings.AUTHENTICATION_BACKENDS = self._original_auth_backends

    def test_handler404(self):
        # import the root urlconf like django does when it starts up
        root_urlconf = __import__(settings.ROOT_URLCONF,
                                  globals(), locals(), ['urls'], -1)
        # ...so that we can access the 'handler404' defined in there
        par, end = root_urlconf.handler404.rsplit('.', 1)
        # ...which is an importable reference to the real handler404 function
        views = __import__(par, globals(), locals(), [end], -1)
        # ...and finally we the handler404 function at hand
        handler404 = getattr(views, end)

        # to call this view function we need a mock request object
        fake_request = RequestFactory().request(**{'wsgi.input': None})

        # the reason for first causing an exception to be raised is because
        # the handler404 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise Http404("something bad")
        except Http404:
            # mock the django_arecibo wrapper so it doesn't actually
            # call out on the network
            with patch('django_arecibo.wrapper') as m:
                # do this inside a frame that has a sys.exc_info()
                response = handler404(fake_request)
                eq_(response.status_code, 404)
                ok_('Page not found' in response.content)
                eq_(m.post.call_count, 1)

        try:
            # raise an error but this time withou a message
            raise Http404
        except Http404:
            with patch('django_arecibo.wrapper') as m:
                response = handler404(fake_request)
                eq_(response.status_code, 404)
                ok_('Page not found' in response.content)
                eq_(m.post.call_count, 1)

        try:
            # Resolver404 is a subclass of Http404 that is raised by django
            # when it can't match a URL to a view
            raise Resolver404("/never/heard/of/")
        except Resolver404:
            with patch('django_arecibo.wrapper') as m:
                response = handler404(fake_request)
                eq_(response.status_code, 404)
                ok_('Page not found' in response.content)
                eq_(m.post.call_count, 0)

    def test_handler500(self):
        # The reason for doing this COMPRESS_DEBUG_TOGGLE "hack" is because
        # our 500.html extends "base.html" which uses ``compress`` blocks.
        # A way of switching that off entirely is to set COMPRESS_DEBUG_TOGGLE
        # and then match that with a GET variable with the same value.
        # That does the same as running django_compressor in offline mode
        # which is to basically do nothing and assume the compressed file just
        # exists.
        _previous_setting = getattr(settings, 'COMPRESS_DEBUG_TOGGLE', None)
        settings.COMPRESS_DEBUG_TOGGLE = 'no-compression'
        try:
            # import the root urlconf like django does when it starts up
            root_urlconf = __import__(settings.ROOT_URLCONF,
                                      globals(), locals(), ['urls'], -1)
            # ...so that we can access the 'handler500' defined in there
            par, end = root_urlconf.handler500.rsplit('.', 1)
            # ...which is an importable reference to the real handler500 function
            views = __import__(par, globals(), locals(), [end], -1)
            # ...and finally we the handler500 function at hand
            handler500 = getattr(views, end)

            # to make a mock call to the django view functions you need a request
            fake_request = RequestFactory().get('/', {'no-compression': 'true'})

            # the reason for first causing an exception to be raised is because
            # the handler500 function is only called by django when an exception
            # has been raised which means sys.exc_info() is something.
            try:
                raise NameError("sloppy code!")
            except NameError:
                # do this inside a frame that has a sys.exc_info()
                with patch('django_arecibo.wrapper') as m:
                    response = handler500(fake_request)
                    eq_(response.status_code, 500)
                    ok_('Oops' in response.content)
                    eq_(m.post.call_count, 1)
        finally:
            # If this was django 1.4 I would do:
            #   from django.test.utils import override_settings
            #   ...
            #   @override_settings(COMPRESS_DEBUG_TOGGLE='...')
            #   def test_handler500(self):
            #       ...
            settings.COMPRESS_DEBUG_TOGGLE = _previous_setting

    def test_secure_session_cookies(self):
        """secure session cookies should always be 'secure' and 'httponly'"""
        url = reverse('accounts.views.login')
        # run it as a mocked AJAX request because that's how elmo does it
        response = self.client.post(url,
          {'username': 'peterbe',
           'password': 'secret'},
          **{'X-Requested-With': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        ok_('class="error' in response.content)

        from django.contrib.auth.models import User
        user = User.objects.create(username='peterbe',
                                   first_name='Peter')
        user.set_password('secret')
        user.save()

        response = self.client.post(url,
          {'username': 'peterbe',
           'password': 'secret',
           'next': '/foo'},
          **{'X-Requested-With': 'XMLHttpRequest'})
        # even though it's
        eq_(response.status_code, 302)
        ok_(response['Location'].endswith('/foo'))

        # if this fails it's because settings.SESSION_COOKIE_SECURE
        # isn't true
        assert settings.SESSION_COOKIE_SECURE
        ok_(self.client.cookies['sessionid']['secure'])

        # if this fails it's because settings.SESSION_COOKIE_HTTPONLY
        # isn't true
        assert settings.SESSION_COOKIE_HTTPONLY
        ok_(self.client.cookies['sessionid']['httponly'])

        # should now be logged in
        url = reverse('accounts.views.user_json')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # "Hi Peter" or something like that
        ok_('Peter' in response.content)

    def test_index_page(self):
        """load the current homepage index view"""
        url = reverse('homepage.views.index')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_index_page_feed_reader(self):
        url = reverse('homepage.views.index')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        content = response.content
        if isinstance(content, str):
            content = unicode(content, 'utf-8')

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
        ok_(truncatewords(first['title'], 8) in content)
        ok_('href="%s"' % first['link'] in content)

        second = parsed.entries[1]
        ok_(truncatewords(second['title'], 8) in content)
        ok_('href="%s"' % second['link'] in content)

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

        url = reverse('homepage.views.teams')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        content = response.content.split('id="teams"')[1]
        content = content.split('<footer')[0]

        url_fr = reverse('homepage.views.locale_team', args=['fr'])
        url_sv = reverse('homepage.views.locale_team', args=['sv-SE'])
        url_br = reverse('homepage.views.locale_team', args=['br-BR'])
        ok_(url_fr in content)
        ok_(url_sv in content)
        ok_(url_br in content)
        url_en = reverse('homepage.views.locale_team', args=['en-US'])
        ok_(url_en not in content)
        ok_(-1 < content.find('br-BR')
               < content.find('French')
               < content.find('Swedish'))
        ok_('en-US' not in content)

    def test_team_page(self):
        """test a team (aka. locale) page"""
        Locale.objects.create(
          code='sv-SE',
          name='Swedish',
        )
        url = reverse('homepage.views.locale_team', args=['xxx'])
        response = self.client.get(url)
        # XXX would love for this to be a 404 instead (peterbe)
        eq_(response.status_code, 302)
        url = reverse('homepage.views.locale_team', args=['sv-SE'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response.content)
        ok_('Swedish' in response.content)
        # it should also say "Swedish" in the <h1>
        h1_text = re.findall('<h1[^>]*>(.*?)</h1>',
                             response.content,
                             re.M | re.DOTALL)[0]
        ok_('Swedish' in h1_text)

    def test_pushes_redirect(self):
        """test if the old /pushes url redirects to /source/pushes"""
        old_response = self.client.get('/pushes/repo?path=query')
        eq_(old_response.status_code, 301)
        target_url = reverse('pushes.views.pushlog', kwargs={'repo_name': 'repo'})
        new_response = self.client.get(target_url, {'path': 'query'})
        eq_(new_response.status_code, 200)
        eq_(urlparse.urlparse(old_response['Location'])[2:],
            ('/source/pushes/repo', '', 'path=query', ''))

    def test_diff_redirect(self):
        """test if the old /pushes url redirects to /source/pushes"""
        old_response = self.client.get('/shipping/diff?to=62f87d2952f4&from=fc700f4da954&tree=fx_beta&repo=some_repo&url=&locale=')
        eq_(old_response.status_code, 301)
        target_url = reverse('pushes.views.diff')
        # not testing response, as we don't have a repo to back this up
        opath, oparam, oquery, ohash = \
            urlparse.urlparse(old_response['Location'])[2:]
        eq_((opath, oparam), urlparse.urlparse(target_url)[2:4])
        eq_(urlparse.parse_qs(oquery),
            {
                'to': ['62f87d2952f4'],
                'from': ['fc700f4da954'],
                'tree': ['fx_beta'],
                'repo': ['some_repo']})

    def test_get_homepage_locales(self):
        for i in range(1, 40 + 1):
            loc = Locale.objects.create(
              name='Language-%d' % i,
              code='L%d' % i
            )
        assert Locale.objects.all().count() == 40
        # add one that doesn't count
        Locale.objects.create(
          name=None,
          code='en-us'
        )

        from homepage.views import get_homepage_locales
        first, second, rest = get_homepage_locales(4)
        eq_(len(first), 4)
        eq_(len(second), 4 - 1)
        eq_(rest, 40 - len(first) - len(second))

        # if you want to split by the first 30
        # which, doubled, is more than the total number of locales,
        # it gets reduced to the minimum which is 20
        first, second, rest = get_homepage_locales(30)
        eq_(len(first), 20)
        eq_(len(second), 20 - 1)
        eq_(rest, 1)
