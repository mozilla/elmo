/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var apibase = 'https://api-dev.bugzilla.mozilla.org/1.3/';
$(document).ready(function() {
  var core_counts, flag_bugs;
  function processBugs() {
    if (!core_counts || !flag_bugs) return;
    var count = 0, flag_vals, flag, loc, bugs_per_flag = {};
    for (var i = 0, ii = flag_bugs.bugs.length; i < ii; ++i) {
      flag_vals = flag_bugs.bugs[i].cf_locale;
      for (var j = 0, jj = flag_vals.length; j < jj; ++j) {
        flag = flag_vals[j];
        loc = flag.split(' ')[0];
        if (bugs_per_flag.hasOwnProperty(loc)) {
          bugs_per_flag[loc].push(flag);
        }
        else {
          bugs_per_flag[loc] = [flag];
        }
      }
    }
    var comps = core_counts.data.length;
    var o = {properties: {count: {valueType: 'number'}}};
    var items = [];
    for (var i = 0; i < comps; ++i) {
      var _comp = core_counts.x_labels[i];
      loc = _comp.split(' ')[0];
      var _count = Number(core_counts.data[i]);
      if (bugs_per_flag.hasOwnProperty(loc)) {
        _count += bugs_per_flag[loc].length;
        delete bugs_per_flag[loc];
      }
      items.push({id: loc, locale: loc, label: _comp, count: _count});
      count += _count;
    }
    for (loc in bugs_per_flag) {
      if (bugs_per_flag.hasOwnProperty(loc)) {
        _count = bugs_per_flag[loc].length;
        items.push({id: loc, locale: loc, label: bugs_per_flag[loc][0], count: _count});
        count += _count;
      }
    }
    $('#nob').text(count);
    $('#noc').text(comps);
    o.items = items;
    window.database.loadData(o);
  };
  var cparams = {
    product: 'Mozilla Localizations',
    'field0-0-0': 'component',
    'type0-0-0': 'regexp',
    'value0-0-0': '^[a-z]{2,3}[ \-]',
    resolution: '---',
    x_axis_field: 'component'
  };
  $.getJSON(apibase + 'count', cparams,
            function(data) {
              core_counts = data;
              processBugs();
            });
  var fparams = {
    'field0-0-0': 'cf_locale',
    'type0-0-0': 'isnotempty',
    resolution: '---',
    include_fields: 'cf_locale' + ',id,summary' // the latter only for debugging
  };
  $.getJSON(apibase + 'bug', fparams,
            function(data) {
              flag_bugs = data;
              processBugs();
            });
});
