from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^login', 'django.contrib.auth.views.login',
     {'template_name': 'accounts/user.html'}),
    (r'^user.html$', 'accounts.views.user_html'),
    (r'^logout$', 'accounts.views.logout'),
)
