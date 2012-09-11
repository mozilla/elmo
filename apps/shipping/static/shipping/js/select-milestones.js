/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function select_branch(branch) {
  var container = $('table.appversions');
  $('tr', container).hide();
  // if you have changed your mind, make sure no old checks are left on
  // because invisiblity to the naked eye doesn't mean it doesn't get sent
  $('input[type="checkbox"]:hidden').each(function() {
    this.checked = false;
  });
  $('tr.' + branch, container).show();
}

$(function() {
  var current = $('select[name="branch"]').val();
  if (current) {
    select_branch(current);
  }
  $('select[name="branch"]').change(function() {
    select_branch($(this).val());
  });

});
