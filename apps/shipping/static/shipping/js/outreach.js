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
 * The Original Code is elmo.
 *
 * The Initial Developer of the Original Code is
 * Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2011
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *  Axel Hecht <l10n@mozilla.com>
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
