from django.conf.urls.defaults import *

urlpatterns = patterns('privacy.views',
                       (r'^(?P<id>\d+)?$', 'show_policy'),
                       (r'^versions$', 'versions'),
                       (r'^add$', 'add_policy'),
                       (r'^activate$', 'activate_policy'),
                       (r'^comment$', 'add_comment'),
                       (r'^shared.css$', 'policy_css'),
                       )
