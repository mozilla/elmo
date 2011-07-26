# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''URL mappings for the shipping app.
'''

from django.conf.urls.defaults import *

urlpatterns = patterns('shipping.views',
    (r'^\/?$', 'index'),
    (r'^\/dashboard\/?$', 'dashboard'),
    (r'^\/diff$', 'diff_app'),
    (r'^\/milestones$', 'milestones'),
    (r'^\/stones-data$', 'stones_data'),
    (r'^\/open-mstone$', 'open_mstone'),
    (r'^\/confirm-ship$', 'confirm_ship_mstone'),
    (r'^\/confirm-drill$', 'confirm_drill_mstone'),
    (r'^\/drill$', 'drill_mstone'),
    (r'^\/ship$', 'ship_mstone'),
)

urlpatterns += patterns('shipping.views.status',
    (r'^/l10n-changesets$', 'l10n_changesets'),
    (r'^/shipped-locales$', 'shipped_locales'),
    (r'^/api/signoffs$', 'signoff_json'),
)

urlpatterns += patterns('shipping.views.outreach',
    (r'^/outreach/$', 'select_apps'),
    (r'^/outreach/data$', 'data'),
)

urlpatterns += patterns('shipping.views.milestone',
    (r'^\/about-milestone/(.*)', 'about'),
    (r'^\/milestone-statuses/(.*)', 'statuses'),
    (r'^\/json-changesets$', 'json_changesets'),
)

urlpatterns += patterns('shipping.views.app',
    (r'^\/app/locale-changes/(.*)', 'changes'),
)

urlpatterns += patterns('shipping.views.signoff',
    (r'^\/signoffs\/(.*?)\/(.*)', 'signoff'),
    (r'^\/signoffs-details\/(.*?)\/(.*)', 'signoff_details'),
    (r'^\/add-signoff\/(.*?)\/(.*)', 'add_signoff'), # POST only
    (r'^\/review-signoff\/(.*?)\/(.*)', 'review_signoff'), # POST only
)
