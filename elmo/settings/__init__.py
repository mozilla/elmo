# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import markus

from .base import *  # noqa
# we modify that later, explicitly import
from .base import CACHES
try:
    from .local import *  # noqa
except ImportError:
    pass

# overload configuration from environment, as far as we have it
try:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ['ELMO_DB_NAME'],
            'USER': os.environ['ELMO_DB_USER'],
            'PASSWORD': os.environ['ELMO_DB_PASSWORD'],
            'HOST': os.environ['ELMO_DB_HOST'],
            'PORT': '',
            'CONN_MAX_AGE': 500,
            'OPTIONS': {
                'charset': 'utf8',
                'use_unicode': True,
            },
            'TEST': {
                'CHARSET': "utf8",
                'COLLATION': 'utf8_general_ci',
            },
        },
    }
    if 'ELMO_TEST_DB_NAME' in os.environ:
        DATABASES['default']['TEST']['NAME'] = os.environ['ELMO_TEST_DB_NAME']
except KeyError:
    if 'DATABASES' not in vars():
        # we're not configured, let's just set some database
        # we probably need this to run django commands during
        # docker image builds.
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'mydatabase',
            }
        }
for local_var, env_var in (
            ('ES_COMPARE_HOST', 'ES_COMPARE_HOST'),
            ('ES_COMPARE_INDEX', 'ES_COMPARE_INDEX'),
            ('LDAP_HOST', 'ELMO_LDAP_HOST'),
            ('LDAP_DN', 'ELMO_LDAP_DN'),
            ('LDAP_PASSWORD', 'ELMO_LDAP_PASSWORD'),
            ('REPOSITORY_BASE', 'ELMO_REPOSITORY_BASE'),
            ('SECRET_KEY', 'ELMO_SECRET_KEY'),
):
    if env_var in os.environ:
        globals()[local_var] = os.environ[env_var]

if 'ELMO_BUILD_BASE' in os.environ:
    _log_base = os.environ['ELMO_BUILD_BASE']
    LOG_MOUNTS = {
      'l10n-master': _log_base + '/l10n-master',
      'test-master': _log_base + '/test-master',
    }

if 'ELMO_SENTRY_DSN' in os.environ:
    RAVEN_CONFIG = {
        'dsn': os.environ['ELMO_SENTRY_DSN']
    }

if 'ELMO_INCLUDE_ANALYTICS' in os.environ:
    INCLUDE_ANALYTICS = True

if 'ELMO_MEMCACHED' in os.environ:
    CACHES['default']['LOCATION'] = os.environ['ELMO_MEMCACHED']

# check ldap config
if all('LDAP_{}'.format(s) in globals() for s in ('HOST', 'DN', 'PASSWORD')):
    import ldap  # noqa
    AUTHENTICATION_BACKENDS = ('lib.auth.backends.MozLdapBackend',)
else:
    import warnings
    warnings.warn("No LDAP authentication")

# hook up markus to datadog, if set
if (
        'ELMO_DATADOG_NAMESPACE' in os.environ
        and os.environ['ELMO_DATADOG_NAMESPACE']
):
    markus.configure(backends=[{
        'class': 'markus.backends.datadog.DatadogMetrics',
        'options': {
            'statsd_namespace': os.environ['ELMO_DATADOG_NAMESPACE']
        }
    }])

# generic django settings, good for DEBUG etc
boolmapper = {
    'true': True,
    '1': True,
    'false': False,
    '0': False,
}
for key, value in os.environ.items():
    if not key.startswith('DJANGO_'):
        continue
    globals()[key[len('DJANGO_'):]] = boolmapper.get(value.lower(), value)

# remove secrets and passwords from environment
for key in os.environ.keys():
    if 'SECRET' in key or 'PASSWORD' in key:
        del os.environ[key]

__all__ = [
    setting for setting in globals().keys() if setting.isupper()
]
