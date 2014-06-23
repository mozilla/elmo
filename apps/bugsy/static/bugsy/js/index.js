/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var BugImporters = {
  _counts: null,
  _comp: null
};
var bug_count = null;

function parse_counts(url, data, callback, link) {
  var json = JSON.parse(data);
  var items = [], count = 0;
  for (var i=0, ii=json.data.length; i < ii; ++i) {
    items.push({
      label: json.x_labels[i],
      comp: json.data[i]
    });
    count += json.data[i];
  }
  if (bug_count === null) {
    bug_count = count;
  }
  else {
    bug_count += count;
    show_bug_count();
  }
  $('#noc').text(json.data.length);
  callback({items: items});
}
function parse_flags(url, data, callback, link) {
  var json = JSON.parse(data);
  var items = [], hash = {}, flag;
  for (var i=0, ii=json.bugs.length; i < ii; ++i) {
    var bug = json.bugs[i];
    for (var j in bug.cf_locale) {
      flag = bug.cf_locale[j];
      hash[flag] = (hash[flag] || 0) + 1;
    }
  }
  for (flag in hash) {
    items.push({
      label: flag,
      flagged: hash[flag]
    });
  }
  if (bug_count === null) {
    bug_count = json.bugs.length;
  }
  else {
    bug_count += json.bugs.length;
    show_bug_count();
  }
  callback({items: items});
}
function show_bug_count() {
  $('#nob').text(bug_count);
}

function registerBugImporters() {
  BugImporters._counts = new Exhibit.Importer(
    "x-bugzilla/counts",
    "get",
    parse_counts
  );
  BugImporters._comp = new Exhibit.Importer(
    "x-bugzilla/flags",
    "get",
    parse_flags
  );
}

jQuery(document).one("registerImporters.exhibit",
                     registerBugImporters);
