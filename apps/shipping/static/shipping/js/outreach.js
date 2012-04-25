/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function createOutreachData() {
  var avs = [];
  var appvers = $("#results tr").first().children("th").next()
    .map(function(){
      avs.push(this.textContent);
      return {app: this.dataset.app,
              av: this.textContent};
    });
  var rows = $("#results tr").next();
  var rv = {};
  var locales = [];
  rows.each(function() {
    var row = $(this).children('td');
    var loc = row.first().text().trim();
    locales.push(loc);
    row.next().each(function(i) {
      var entry = $(this);
      var c = entry.text().trim();
      if (!c) {
        return;
      }
      var missing = Number(c);
      if (!(loc in rv)) rv[loc] = {};
      if (!(appvers[i].app in rv[loc])) rv[loc][appvers[i].app] = {};
      rv[loc][appvers[i].app][appvers[i].av] = missing;
    });
  });
  return {appvers: avs, locales: locales, data:rv};
}

$(function() {
  $('#export').click(function() {
    var rv = createOutreachData();
    $("#json").val(JSON.stringify(rv, null, " ")).show();
  });
  $("#json").val("").hide();
});
