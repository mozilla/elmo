# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Tests for the build progress displays.
'''
from __future__ import absolute_import

import os
import datetime
from tempfile import gettempdir
from nose.tools import eq_, ok_
from elmo.test import TestCase
from commons.tests.mixins import EmbedsTestCaseMixin
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client
from mbdb.models import (Build, Change, Master, Log, Property, SourceStamp,
                         Builder, Slave)
from tinder.views import _waterfall, LogMountKeyError
from tinder.templatetags import build_extras


class WaterfallStarted(TestCase):
    fixtures = ['one_started_l10n_build.json']

    def testInner(self):
        '''Basic tests of _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)
        self.assertEqual(blame.width, 1,
                         'Width of blame column is not 1')
        self.assertEqual(len(buildercolumns), 1,
                         'Not one builder found')
        name, builder = buildercolumns.items()[0]
        self.assertEqual(name, 'dummy')
        self.assertEqual(builder.width, 1,
                         'Width of builder column is not 1')
        blame_rows = list(blame.rows())
        self.assertEqual(len(blame_rows), 3,
                         'Expecting 3 rows for table, got %d' %
                         len(blame_rows))
        self.assertNotEqual(blame_rows[0], [],
                            'First row should not be empty')
        self.assertEqual(blame_rows[1], [])
        self.assertEqual(blame_rows[2], [])
        build_rows = list(builder.rows())
        self.assertEqual(build_rows[0][0]['obj'].buildnumber, 1)
        self.assertEqual(build_rows[1][0]['obj'].buildnumber, 0)
        self.assertEqual(build_rows[2][0]['obj'], None)

    def testHtml(self):
        url = reverse('tinder.views.waterfall')
        response = self.client.get(url)
        eq_(response.status_code, 200)


class WaterfallParallel(TestCase):
    fixtures = ['parallel_builds.json']

    def testInner(self):
        '''Testing parallel builds in _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)

    def testHtml(self):
        '''Testing parallel builds in _waterfall'''
        url = reverse('tinder.views.waterfall')
        response = self.client.get(url)
        eq_(response.status_code, 200)


class FullBuilds(TestCase):
    fixtures = ['full_parallel_builds.json']

    def testInner(self):
        '''Testing full build list in _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)

    def testForBuild(self):
        pass


class Mix:
    def waterfall_to_file(self):
        """Debugging helpers for waterfalls, dump the waterfall for all
        fixtures used into html files in the working dir, so that you can see
        what you're testing."""
        c = Client()
        response = c.get('/builds/waterfall')
        leaf = self.fixtures[0].replace(".json", ".html")
        open(leaf, "w").write(response.content)


class OneStartedL10nBuild(TestCase, Mix):
    fixtures = ['one_started_l10n_build.json']


class ParallelBuilds(TestCase, Mix):
    fixtures = ['parallel_builds.json']


class FullParallelBuilds(TestCase, Mix):
    fixtures = ['full_parallel_builds.json']


class FakeBuildOrStep:
    """Helper class to get around having to use fixtures or the like.

    Mimicks the build and step properties that our filters use.
    """
    def __init__(self, result, starttime):
        self.result = result
        self.starttime = starttime


class res2class(TestCase):
    """Testing the res2class filter in build_extras.py"""
    def _test(self, result, starttime, value):
        b = FakeBuildOrStep(result, starttime)
        self.assertEqual(build_extras.res2class(b), value)

    def test_success(self):
        self._test(0, None, "success")

    def test_warning(self):
        self._test(1, None, "warning")

    def test_failure(self):
        self._test(2, None, "failure")

    def test_skip(self):
        self._test(3, None, "skip")

    def test_except(self):
        self._test(4, None, "except")

    def test_invalid(self):
        self._test(5, None, "")

    def test_empty(self):
        self._test(None, None, "")

    def test_running(self):
        self._test(None, datetime.datetime.utcnow(), "running")


class showbuild(TestCase):
    """Testing the showbuild filter in build_extras.py"""
    fixtures = ["one_started_l10n_build.json"]

    def test_success(self):
        b = Build.objects.filter(result=0)[0]
        out = build_extras.showbuild(b)
        self.assertTrue(out.startswith('''<a href='''), "Not a link: " + out)

    def test_running(self):
        b = Build.objects.get(endtime__isnull=True)
        out = build_extras.showbuild(b)
        self.assertTrue('''class="step_text"''' in out,
                        "No step info in " + out)
        self.assertTrue('''class="running"''' in out,
                        "No 'running' class in " + out)

    def test_change(self):
        c = Change.objects.all()[0]
        out = build_extras.showbuild(c)
        self.assertTrue("John Doe" in out, "User 'John Doe' was not in " + out)
        self.assertTrue("builds_for?change=1" in out,
                        "Not the right URL in " + out)


class timedelta(TestCase):
    """Testing the timedelta filter in build_extras.py"""
    def test_empty(self):
        now = datetime.datetime.utcnow()
        self.assertEqual(build_extras.timedelta(None, now), "-")
        self.assertEqual(build_extras.timedelta(now, None), "-")

    def test_days(self):
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(3)
        self.assertEqual(build_extras.timedelta(start, end), "3 day(s)")

    def test_minutes(self):
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(minutes=3)
        self.assertEqual(build_extras.timedelta(start, end), "3 minute(s)")

    def test_seconds(self):
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(seconds=3)
        self.assertEqual(build_extras.timedelta(start, end), "3 second(s)")


class ViewsTestCase(TestCase, EmbedsTestCaseMixin):
    fixtures = ['one_started_l10n_build.json']

    def setUp(self):
        super(ViewsTestCase, self).setUp()
        self.temp_directory = os.path.join(gettempdir(), 'test-builds')
        if not os.path.isdir(self.temp_directory):
            os.mkdir(self.temp_directory)
        self.old_mounts = getattr(settings, 'LOG_MOUNTS', None)
        setattr(settings, 'LOG_MOUNTS', {})

    def tearDown(self):
        super(ViewsTestCase, self).tearDown()
        if self.old_mounts is None:
            del settings.LOG_MOUNTS
        else:
            setattr(settings, 'LOG_MOUNTS', self.old_mounts)
        import shutil
        shutil.rmtree(self.temp_directory)

    def test_pmap(self):
        from .views import pmap

        prop1 = Property.objects.create(
          name='gender',
          source='internet',
          value='male',
        )
        prop2 = Property.objects.create(
          name='age',
          source='books',
          value=31,
        )
        prop3 = Property.objects.create(
          name='avoid',
          source='at all',
          value=['costs'],
        )

        Property.objects.all()

        # delete any excess builds from fixtures
        Build.objects.all().delete()

        # test that it works with no builds
        props = ('gender', 'age')
        result = pmap(props, [])
        eq_(result, {})

        ss = SourceStamp.objects.all()[0]
        builder = Builder.objects.all()[0]
        slave = Slave.objects.all()[0]
        build1 = Build.objects.create(
          buildnumber=1,
          builder=builder,
          slave=slave,
          sourcestamp=ss,
        )
        build1.properties.add(prop1)

        build2 = Build.objects.create(
          buildnumber=2,
          builder=builder,
          slave=slave,
          sourcestamp=ss,
        )
        build2.properties.add(prop2)
        build2.properties.add(prop3)

        build3 = Build.objects.create(
          buildnumber=3,
          builder=builder,
          slave=slave,
          sourcestamp=ss,
        )
        build3.properties.add(prop1)
        build3.properties.add(prop3)

        props = ('gender', 'age')
        result = pmap(props, [build1.id, build2.id])
        ok_(isinstance(result, dict))

        # since we fed build1.id and build2.id expect these to be the keys
        eq_(sorted(result.keys()), sorted((build1.id, build2.id)))
        # for build1 we attached the first property (name)
        eq_(result[build1.id], {u'gender': u'male'})
        # for build2 we attached the second property and the third
        # but the third is ignored as per the second argument to pmap()
        eq_(result[build2.id], {u'age': 31})

        result = pmap(('age',), [build1.id])
        eq_(result, {})

        result = pmap(('gender',), [build2.id])
        eq_(result, {})

        build2.properties.add(prop1)
        result = pmap(('gender',), [build2.id])
        eq_(result.keys(), [build2.id])
        eq_(result[build2.id], {u'gender': u'male'})

    def test_showlog(self):
        """Test that showlog shows headers, stdout, stderr,
        with the right CSS classes, but not data from other channels like json.
        """
        master = Master.objects.all()[0]

        build = Build.objects.all()[0]
        step = build.steps.all()[0]
        log = Log.objects.create(
          name='foo',
          filename='foo.log',
          step=step,
        )
        url = reverse('tinder.views.showlog',
                      args=[step.id, log.name])
        with file(os.path.join(self.temp_directory, log.filename), 'w') as f:
            f.write(SAMPLE_BUILD_LOG_PAYLOAD)

        try:
            lm = settings.LOG_MOUNTS
            del settings.LOG_MOUNTS
        except AttributeError:
            pass
        settings.LOG_MOUNTS = {master.name: self.temp_directory}
        response = self.client.get(url)
        try:
            settings.LOG_MOUNTS = lm
        except NameError:
            pass
        content = response.content
        content = content.split('</header>')[1].split('</footer')[0]

        ok_('<span class="pre header">header content\n</span>' in content)
        ok_('<span class="pre stdout">stdout content\n</span>' in content)
        ok_('<span class="pre stderr">stderr content\n</span>' in content)
        ok_('json' not in content)

    def test_showlog_invalid_master(self):
        build = Build.objects.all()[0]
        step = build.steps.all()[0]
        log = Log.objects.create(
          name='foo',
          filename='foo.log',
          step=step,
        )
        url = reverse('tinder.views.showlog',
                      args=[step.id, log.name])
        self.assertRaises(
            LogMountKeyError,
            self.client.get,
            url
        )

    def test_showhtmllog(self):
        """Test that showlog shows html content if that's in the db,
        unescaped.
        """
        build = Build.objects.all()[0]
        step = build.steps.all()[0]
        htmlcontent = '<span class="foo">&amp;</span>'
        log = Log.objects.create(
          name='foo',
          html=htmlcontent,
          isFinished=True,
          step=step,
        )
        url = reverse('tinder.views.showlog',
                      args=[step.id, log.name])
        response = self.client.get(url)
        content = response.content
        content = content.split('</header>')[1].split('</footer')[0]

        ok_(htmlcontent in content)

    def test_render_tbpl(self):
        url = reverse('tinder.views.tbpl')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response)

    def test_render_showbuild(self):
        build, = Build.objects.all()[:1]
        builder = build.builder
        url = reverse('tinder.views.showbuild',
                      args=[builder.name, build.buildnumber])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        self.assert_all_embeds(response)

    def test_render_showbuild_bad_buildername(self):
        build, = Build.objects.all()[:1]
        url = reverse('tinder.views.showbuild',
                      args=['junkjunk', build.buildnumber])
        response = self.client.get(url)
        eq_(response.status_code, 404)

    def test_render_showbuild_bad_buildnumber(self):
        build, = Build.objects.all()[:1]
        builder = build.builder
        url = reverse('tinder.views.showbuild',
                      args=[builder.name, 666])
        response = self.client.get(url)
        eq_(response.status_code, 404)

    def test_render_builds_for_change(self):
        url = reverse('tinder.views.builds_for_change')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        change, = Change.objects.all()[:1]
        response = self.client.get(url, {'change': change.number})
        eq_(response.status_code, 200)

        feed_url = reverse('BuildsForChangeFeed', args=(change.number,))
        ok_(feed_url in response.content)


SAMPLE_BUILD_LOG_PAYLOAD = '''16:2header content
,16:1stderr content
,16:0stdout content
,11:5{"json":1},'''
