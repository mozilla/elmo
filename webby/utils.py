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
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Zbigniew Braniecki <gandalf@mozilla.com>
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

from webby.models import Weblocale
from life.models import Locale
import urllib
import re
import ConfigParser
import os

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
locale_mapping = {}


def intersect(a, b):
    """ returns what's in both a and b """
    return list(set(a) & set(b))


def _read_webpage(url):
    f = urllib.urlopen(url)
    s = f.read()
    f.close()
    return s


patterns = {
  'verbatim': re.compile('<td class="stats-name">\s+<a href="([^"]+)">([^<]+)</a>'),
  'svn': re.compile('<li><a href="([^"]+)/">([^<]+)/</a></li>')
}


exclude_codes = ('templates', 'en-US')

def _get_locale_mapping():
    config = ConfigParser.ConfigParser()
    config.readfp(open(os.path.join(PROJECT_PATH, 'mapping.cfg')))
    for item in config.items("mapping"):
        locale_mapping[item[0]] = item[1]

def _extract_locales_from_verbatim(source):
    locales = []
    if not locale_mapping:
        _get_locale_mapping()

    matches = patterns['verbatim'].findall(source)
    for match in matches:
        url = match[0]
        code = url[1:url.index('/', 1)]
        code = (locale_mapping[code.lower()]
                if code.lower() in locale_mapping else code)
        if code not in exclude_codes:
            locales.append(unicode(code))
    return locales


def update_verbatim(project, code):
    s = _read_webpage(project.verbatim_url)
    locales = _extract_locales_from_verbatim(s)

    wlobj = Weblocale.objects.get(locale_code=code, project=project)
    wlobj.in_verbatim = (code in locales)
    wlobj.save()


def update_verbatim_all(project):
    s = _read_webpage(project.verbatim_url)
    locales = _extract_locales_from_verbatim(s)
    cur_locales = project.locales.values_list('code', flat=True)
    shared = intersect(locales, cur_locales)

    unavailable_locales = []
    for locale in locales:
        if locale not in shared:
            """
            A locale is in verbatim but not in project locales
            """
            try:
                lobj = Locale.objects.get(code=locale)
            except Locale.DoesNotExist:
                unavailable_locales.append(locale)
            else:
                wlobj = Weblocale(locale=lobj,
                                  project=project,
                                  in_verbatim=True)
                wlobj.save()
        else:
            """
            A locale is both in verbatim and project locales
            """
            wlobj = Weblocale.objects.get(locale__code=locale, project=project)
            wlobj.in_verbatim = True
            wlobj.save()
    for locale in cur_locales:
        if locale not in shared:
            """
            A locale is in project locales but is not in verbatim
            """
            wlobj = Weblocale.objects.get(locale__code=locale, project=project)
            wlobj.in_verbatim = False
            wlobj.save()

    #print(unavailable_locales)


def _extract_locales_from_svn(source):
    locales = []
    if not locale_mapping:
        _get_locale_mapping()

    matches = patterns['svn'].findall(source)
    for match in matches:
        code = match[0]
        code = (locale_mapping[code.lower()]
                if code.lower() in locale_mapping else code)
        if code not in exclude_codes:
            locales.append(unicode(code))
    return locales


def update_svn_all(project):
    source = _read_webpage(project.l10n_repo_url)
    locales = _extract_locales_from_svn(source)
    cur_locales = project.locales.values_list('code', flat=True)
    shared = intersect(locales, cur_locales)

    unavailable_locales = []
    for locale in locales:
        if locale not in shared:
            """
            A locale is in verbatim but not in project locales
            """
            try:
                lobj = Locale.objects.get(code=locale)
            except Locale.DoesNotExist:
                unavailable_locales.append(locale)
            else:
                wlobj = Weblocale(locale=lobj,
                                  project=project,
                                  in_vcs=True)
                wlobj.save()
        else:
            """
            A locale is both in verbatim and project locales
            """
            wlobj = Weblocale.objects.get(locale__code=locale, project=project)
            wlobj.in_vcs = True
            wlobj.save()
    for locale in cur_locales:
        if locale not in shared:
            """
            A locale is in project locales but is not in verbatim
            """
            wlobj = Weblocale.objects.get(locale__code=locale, project=project)
            wlobj.in_vcs = False
            wlobj.save()

    #print(unavailable_locales)
