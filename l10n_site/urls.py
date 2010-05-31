from django.conf.urls.defaults import *
from django.conf import settings
from django.http import HttpResponse
import base64
import re

from django.contrib.auth.forms import AuthenticationForm, UserChangeForm

for form in (AuthenticationForm, UserChangeForm):
    user = form.base_fields['username']
    user.max_length = 75
    user.regex = re.compile(r'^[a-zA-Z0-9.@_%-+]+$')
    user.widget.attrs['maxlength'] = 75 
    user.help_text = user.help_text.replace('30','75')

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

dino = '''
AAABAAEAEBAAAAAAAABoBQAAFgAAACgAAAAQAAAAIAAAAAEACAAAAAAAAAEAAAAAAAAAAAAAAAEA
AAABAAAAAAAAAACAAACAAAAAgIAAgAAAAIAAgACAgAAAwMDAAMDcwADwyqYABAQEAAgICAAMDAwA
ERERABYWFgAcHBwAIiIiACkpKQBVVVUATU1NAEJCQgA5OTkAgHz/AFBQ/wCTANYA/+zMAMbW7wDW
5+cAkKmtAAAAMwAAAGYAAACZAAAAzAAAMwAAADMzAAAzZgAAM5kAADPMAAAz/wAAZgAAAGYzAABm
ZgAAZpkAAGbMAABm/wAAmQAAAJkzAACZZgAAmZkAAJnMAACZ/wAAzAAAAMwzAADMZgAAzJkAAMzM
AADM/wAA/2YAAP+ZAAD/zAAzAAAAMwAzADMAZgAzAJkAMwDMADMA/wAzMwAAMzMzADMzZgAzM5kA
MzPMADMz/wAzZgAAM2YzADNmZgAzZpkAM2bMADNm/wAzmQAAM5kzADOZZgAzmZkAM5nMADOZ/wAz
zAAAM8wzADPMZgAzzJkAM8zMADPM/wAz/zMAM/9mADP/mQAz/8wAM///AGYAAABmADMAZgBmAGYA
mQBmAMwAZgD/AGYzAABmMzMAZjNmAGYzmQBmM8wAZjP/AGZmAABmZjMAZmZmAGZmmQBmZswAZpkA
AGaZMwBmmWYAZpmZAGaZzABmmf8AZswAAGbMMwBmzJkAZszMAGbM/wBm/wAAZv8zAGb/mQBm/8wA
zAD/AP8AzACZmQAAmTOZAJkAmQCZAMwAmQAAAJkzMwCZAGYAmTPMAJkA/wCZZgAAmWYzAJkzZgCZ
ZpkAmWbMAJkz/wCZmTMAmZlmAJmZmQCZmcwAmZn/AJnMAACZzDMAZsxmAJnMmQCZzMwAmcz/AJn/
AACZ/zMAmcxmAJn/mQCZ/8wAmf//AMwAAACZADMAzABmAMwAmQDMAMwAmTMAAMwzMwDMM2YAzDOZ
AMwzzADMM/8AzGYAAMxmMwCZZmYAzGaZAMxmzACZZv8AzJkAAMyZMwDMmWYAzJmZAMyZzADMmf8A
zMwAAMzMMwDMzGYAzMyZAMzMzADMzP8AzP8AAMz/MwCZ/2YAzP+ZAMz/zADM//8AzAAzAP8AZgD/
AJkAzDMAAP8zMwD/M2YA/zOZAP8zzAD/M/8A/2YAAP9mMwDMZmYA/2aZAP9mzADMZv8A/5kAAP+Z
MwD/mWYA/5mZAP+ZzAD/mf8A/8wAAP/MMwD/zGYA/8yZAP/MzAD/zP8A//8zAMz/ZgD//5kA///M
AGZm/wBm/2YAZv//AP9mZgD/Zv8A//9mACEApQBfX18Ad3d3AIaGhgCWlpYAy8vLALKysgDX19cA
3d3dAOPj4wDq6uoA8fHxAPj4+ADw+/8ApKCgAICAgAAAAP8AAP8AAAD//wD/AAAA/wD/AP//AAD/
//8ACgoKCgoKCgoKCgoKCgoKCgoKCgoHAQEMbQoKCgoKCgoAAAdDH/kgHRIAAAAAAAAAAADrHfn5
ASQQAAAAAAAAAArsBx0B+fkgHesAAAAAAAD/Cgwf+fn5IA4dEus/IvcACgcMAfkg+QEB+SABHush
bf8QHR/5HQH5+QEdHetEHx4K7B/5+QH5+fkdDBL5+SBE/wwdJfkf+fn5AR8g+fkfEArsCh/5+QEe
JR/5+SAeBwAACgoe+SAlHwFAEhAfAAAAAPcKHh8eASYBHhAMAAAAAAAA9EMdIB8gHh0dBwAAAAAA
AAAA7BAdQ+wHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP//AADwfwAAwH8AAMB/AAAAPwAAAAEAAAAA
AAAAAAAAAAAAAAAAAAAAAQAAgAcAAIAPAADADwAA8D8AAP//AAA='''

urlpatterns = patterns('',
    # Example:
    # (r'^dashboard/', include('dashboard.foo.urls')),
                       (r'^favicon.ico$', lambda r: HttpResponse(base64.standard_b64decode(dino),
                                                                 mimetype="image/x-icon"),
                        {}, 'favicon'),
                       (r'^privacy/', include('privacy.urls')),
                       (r'.*/__history__.html$', lambda r: HttpResponse()),
                       (r'^builds/',
                        include('tinder.urls')),
                       (r'^pushes/(?P<repo_name>.+)?$',
                        'pushes.views.pushlog', {}, 'pushlog'),
                       (r'^dashboard/', include('l10nstats.urls')),
                       (r'^shipping',
                            include('shipping.urls')),
                       (r'^bugs/',
                            include('bugsy.urls')),
                       (r'^accounts/',
                            include('accounts.urls')),
                       (r'^',
                        include('homepage.urls')),
                       (r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /*",
                                                                 mimetype="text/plain")),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
)

# Usually, you would include this only for DEBUG, but let's keep
# this so that we can reverse resolve static.
# That way, we can move the site to /stage/foo without messing with
# the references to /static/.
urlpatterns += patterns('',
                        (r'^static/(?P<path>.*)$',
                         'django.views.static.serve',
                         {'document_root': 'static/'}, 'static'),
                        )
 
