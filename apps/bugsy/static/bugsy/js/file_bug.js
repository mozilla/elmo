/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global Exhibit, URLSearchParams */

var BugComponentImporter = {
  _importer: null
};
BugComponentImporter.parse = function(url, data, callback, link) {
  const json = JSON.parse(data);
  const items = json.products[0].components
    .filter(
      comp => / \/ /.test(comp.name)
    )
    .map(
      comp => {
        let loc = comp.name.split(' / ')[0];
        return {
          'id': loc,
          'label': comp.name,
          'product': 'Mozilla Localizations',
          'component': comp.name,
          'type': 'Component'};
      }
    );
  callback({items: items});
};

BugComponentImporter._register = function() {
    BugComponentImporter._importer = new Exhibit.Importer(
      "x-bugzilla-components",
      "get",
      BugComponentImporter.parse
    );
};

$(document).one("registerImporters.exhibit", BugComponentImporter._register);


document.forms.bugdata.short_desc.focus();
document.getElementById('show-extra-fields')
  .addEventListener('click', function() {
    document.getElementById('bugdetails').classList.add('expanded');
  });

function getFormData() {
  var elems = document.forms.bugdata.elements;
  var out = new URLSearchParams();
  for (var i = 0; i < elems.length; ++i) {
    var elem = elems[i];
    if (elem.name == '' || elem.value == '') continue;
    out.set(elem.name, elem.value);
  }
  return out;
}

function getBugURL(params) {
  var url = 'https://bugzilla.mozilla.org/enter_bug.cgi?';
  let search = new URLSearchParams();
  Object.keys(params).forEach(p => search.set(p, params[p]));
  url += search;
  return url;
}

function displayBugLinks(data) {
  const container = document.getElementById('linkpane');
  const locs = Object.keys(data);
  locs.sort();
  locs.forEach(loc => {
    let props = data[loc];
    let comp = database.getObject(loc, 'component');
    if (comp != null) {
      props.component = comp;
    }
    let link = document.createElement('a');
    link.href = getBugURL(props);
    link.target = '_blank';
    link.textContent = loc;
    container.appendChild(link);
    container.appendChild(document.createTextNode(' '));
  });
}

function getBugLinks() {
  document.getElementById('linkpane').innerHTML = '';
  var set = exhibit.getUIContext().getCollection().getRestrictedItems();
  var params = getFormData();
  set.visit(loc => params.append('locales', loc));
  fetch(`${BUG_LINKS_URL}?${params}`)
  .then(r => r.json())
  .then(displayBugLinks)
}
