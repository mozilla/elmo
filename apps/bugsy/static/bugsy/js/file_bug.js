/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
      function getComponent(_, comp) {
        if (!/ \/ /.test(comp.name)) {return;}
        var loc = comp.name.split(' / ')[0];
        var item = {'id': loc,
          'label': comp.name,
          'product': 'Mozilla Localizations',
          'component': comp.name,
          'type': 'Component'};
        items.push(item);
      }
      $.each(json.products[0].components, getComponent);
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
