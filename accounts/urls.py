from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^profile', 'accounts.views.profile'),
    (r'^login', 'django.contrib.auth.views.login',
     {'template_name': 'accounts/login.html'}),
    (r'^logout', 'django.contrib.auth.views.logout',
     {'template_name': 'accounts/logout.html',
      'next_page': 'login'}),
)
