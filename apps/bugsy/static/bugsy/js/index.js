/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var apibase = 'https://api-dev.bugzilla.mozilla.org/1.2/';
$(document).ready(function() {
  function countBugs(data) {
    var count = 0;
    var comps = data.data.length;
    var o = {properties: {count: {valueType: 'number'}}};
    var items = [];
    for (var i = 0; i < comps; ++i) {
      var _comp = data.x_labels[i];
      var _count = Number(data.data[i]);
      items.push({id: _comp.split(' ')[0], label: _comp, count: _count});
      count += _count;
    }
    $('#nob').text(count);
    $('#noc').text(comps);
    o.items = items;
    window.database.loadData(o);
  };
  var params = {
    product: 'Mozilla Localizations',
    'field0-0-0': 'component',
    'type0-0-0': 'regexp',
    'value0-0-0': '^[a-z]{2,3}[ \-]',
    resolution: '---',
    x_axis_field: 'component'
  };
  $.getJSON(apibase + 'count', params, countBugs);
});
