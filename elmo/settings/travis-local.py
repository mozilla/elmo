SECRET_KEY = 'travis'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'elmo',
        'USER': 'travis',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'elmo'
    }
}
PULSE_USER = '_test_'
PULSE_TTL = 0
