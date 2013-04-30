/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function addMulti() {
  var platform = $("#nextmulti").val();
  var row = $('<tr>');
  $('<input type="text">')
    .attr('name', 'multi_' + platform + '_repo')
    .val('releases/mozilla-beta')
    .appendTo($('<td>').appendTo(row));
  $('<input type="text">')
    .attr('name', 'multi_' + platform + '_rev')
    .val('default')
    .appendTo($('<td>').appendTo(row));
  $('<input type="text">')
    .attr('name', 'multi_' + platform + '_path')
    .val('mobile/android/locales/maemo-locales')
    .appendTo($('<td>').appendTo(row));
  $('#multis').append(row);
}

$(function() {
  $("#ship-expander > a").click(function(){
    $(".shipping-tools").toggle("fast");
    $("#ship-expander").toggleClass('open');
    return false;
  });
  $("#add-multi").click(addMulti);
  // We're usually building with the android-multilocale defaults, 
  // just press the button on load.
  addMulti();
});
