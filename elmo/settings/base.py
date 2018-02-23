# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Django settings file for a project based on the playdoh template.
from __future__ import absolute_import

from funfactory.manage import (
    path,
    ROOT,
)
import os.path

from django.utils.functional import lazy

ROOT_URLCONF = 'elmo.urls'
TEST_RUNNER = 'elmo.test.TestRunner'

DEBUG = False

ADMINS = ()
MANAGERS = ADMINS

## Internationalization.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
#USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
#USE_L10N = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'session_csrf.context_processor',
                'django.template.context_processors.static',
                'accounts.context_processors.accounts',
                'homepage.context_processors.analytics',
            ],
        }
    },
]

# This is the common prefix displayed in front of ALL static files
STATIC_URL = '/static/'


# the location where all collected files end up.
# the reason for repeated the word 'static' inside 'collected/'
# is so we, in nginx/apache, can set up the root to be
# <base path>/collected
# then a URL like http://domain/static/js/jquery.js just works
STATIC_ROOT = COMPRESS_ROOT = path('collected', 'static')

## Middlewares, apps, URL configs.

# not using funfactory.settings_base.MIDDLEWARE_CLASSES here because there's
# so few things we need and so many things we'd need to add
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'session_csrf.CsrfMiddleware',

    'commonware.middleware.FrameOptionsHeader',
    'commonware.middleware.ScrubRequestOnException',
)

INSTALLED_APPS = (
    # a manually maintained list of apps "from funfactory"
    'funfactory',
    'compressor',
    'commonware.response.cookies',
    'session_csrf',

    'elmo',

    # Local apps
    'raven.contrib.django.raven_compat',

    # Third-party apps

    # Django contrib apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',

    # L10n

    # elmo specific
    'life',
    'mbdb',
    'pushes',
    'l10nstats',
    'accounts',
    'homepage',
    'privacy',
    'tinder',
    'shipping',
    'bugsy',
    'elmo_commons',
)

SESSION_COOKIE_SECURE = True

## Tests

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',  # fox2mike suggest to use IP instead of localhost
        'TIMEOUT': 500,
        'KEY_PREFIX': 'elmo',
    }
}

# When we have a good cache backend, we can get much faster session storage
# using the cache backend
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

## django_compressor
COMPRESS_ENABLED = True  # defaults to `not DEBUG`
COMPRESS_OFFLINE = True  # make sure you run `./manage.py compress` upon deployment
COMPRESS_CSS_FILTERS = (
  'compressor.filters.css_default.CssAbsoluteFilter',
  'compressor.filters.cssmin.CSSMinFilter',
)
COMPRESS_JS_FILTERS = []  # empty, no actual compression
STATICFILES_FINDERS = (
  'django.contrib.staticfiles.finders.FileSystemFinder',
  'django.contrib.staticfiles.finders.AppDirectoriesFinder',
  'compressor.finders.CompressorFinder',
)

## Feeds
L10N_FEED_URL = 'http://planet.mozilla.org/l10n/atom.xml'
HOMEPAGE_FEED_SIZE = 5

## Google Analytics
INCLUDE_ANALYTICS = False

WEBDASHBOARD_URL = 'https://l10n.mozilla-community.org/webdashboard/'

# settings for the compare-locales progress preview images
PROGRESS_DAYS = 50
PROGRESS_IMG_SIZE = {'x': 100, 'y': 20}
PROGRESS_IMG_NAME = 'l10nstats/progress.png'
