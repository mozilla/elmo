# Hudson build script for running tests
#
# peterbe@mozilla.com
#
# Inspired by Zamboni
# https://github.com/mozilla/zamboni/blob/master/scripts/build.sh


find . -name '*.pyc' -delete;

virtualenv --no-site-packages elmo_env
source elmo_env/bin/activate

git submodule update --init --recursive
echo "
from base import *
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'elmo',
        'USER': 'hudson',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
        'OPTIONS': {
            'init_command': 'SET storage_engine=InnoDB',
            'charset' : 'utf8',
            'use_unicode' : True,
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
}
" > settings/local.py
# the file settings/ldap_settings.py must exist
cp settings/ldap_settings.py-dist settings/ldap_settings.py

pip install -r requirements/prod.txt
pip install -r requirements/compiled.txt

# dependencies for dependencies
pip install -q mock

python manage.py test --noinput
