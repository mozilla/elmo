/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is l10n django site.
 *
 * The Initial Developer of the Original Code is
 *   Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Peter Bengtsson <peterbe@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

// hack around params default in jquery
$.ajaxSettings.traditional = true;
BugComponentImporter = {};
Exhibit.importers['x-bugzilla-components'] = BugComponentImporter;
BugComponentImporter.load = function(link, database, cont) {
  var url = typeof link == 'string' ? link : link.href;
  url = Exhibit.Persistence.resolveURL(url);
  var callback = function(json, statusText) {
    Exhibit.UI.hideBusyIndicator();
    if (statusText != 'success') {
      Exhibit.UI.showHelp(Exhibit.l10n.failedToLoadDataFileMessage(url));
      if (cont) cont();
      return;
    }
    try {
      var items = [], o = {items: items};
      function getComponent(comp) {
        if (!/ \/ /.test(comp)) {return;}
        var loc = comp.split(' / ')[0];
        var item = {'id': loc,
          'label': comp,
          'product': 'Mozilla Localizations',
          'component': comp,
          'type': 'Component'};
        items.push(item);
      }
      $.each(json.product['Mozilla Localizations'].component, getComponent);
      if (o != null) {
        database.loadData(o, Exhibit.Persistence.getBaseURL(url));
      }
    } catch (e) {
      SimileAjax.Debug.exception(
         e, 'Error loading Bugzilla JSON data from ' + url);
    } finally {
      if (cont) {
        cont();
      }
    }
  };

  Exhibit.UI.showBusyIndicator();
  $.getJSON(url, callback);

};

$(document).ready(function() {
  document.forms.bugdata.short_desc.focus();
  $('#show-extra-fields').click(function() {
    $(this).hide();
    $('.extra-field').fadeIn();
  });
});

function getFormData() {
  var elems = document.forms.bugdata.elements;
  var out = {};
  for (var i = 0; i < elems.length; ++i) {
    var elem = elems[i];
    if (elem.name == '') continue;
    out[elem.name] = elem.value;
  }
  return out;
}

function getBugURL(params) {
  var url = 'https://bugzilla.mozilla.org/enter_bug.cgi?';
  url += $.param(params);
  return url;
}

function displayBugLinks(data) {
  var locs = [];
  $.each(data, function(loc, val) {locs.push(loc);});
  locs.sort();
  $.each(locs, function() {
    var loc = this + ''; // get string
    var props = data[loc];
    var comp = database.getObject(loc, 'component');
    if (comp != null) {
      props.component = comp;
    }
    var url = getBugURL(data[loc]);
    var link = $('<a>').attr('href', url).attr('target', '_blank').text(loc);
    $('#linkpane').append(link).append(' ');
  });
}

function getBugLinks() {
  $('#linkpane').html('');
  var set = exhibit.getUIContext().getCollection().getRestrictedItems();
  var params = getFormData();
  params.locales = set.toArray();
  $.getJSON(BUG_LINKS_URL, params, displayBugLinks);
}
