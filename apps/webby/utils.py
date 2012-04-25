# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
  'verbatim': re.compile(
    '<td class="stats-name">\s+<a href="([^"]+)">([^<]+)</a>'),
  'svn': re.compile('<li><a href="([^"/]+)/?">([^</]+)/?</a></li>')
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
