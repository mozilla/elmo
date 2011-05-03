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

# Commented out until I understand the following:
#  1) why is django as a source egg in there when it's already in vendor/src/django
#  2) python-ldap won't compile because we don't have the ldap-lib header files, hm...
#pip install -r requirements/prod.txt
#pip install -r requirements/compiled.txt
pip install -q MySQL-python==1.2.3c1
pip install -q mercurial
pip install -q hmac==20101005
pip install -q hashlib==20081119
pip install -q py-bcrypt==0.2

python manage.py test --noinput dashtags mbdb tinder
