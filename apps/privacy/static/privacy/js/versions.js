/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(function() {
  $('#add-comment').dialog({
    autoOpen: false, modal: true, width: 600,
    buttons: {
      Cancel: function() {
        $(this).dialog('close');
      },
      OK: function() {
        $('form', this).submit();
      }
    }
  });

  $('input.add_comment').click(function() {
    // if this was jQuery >= 1.5 we could use
    // `$(this).data('id')` instead
    var policy_id = $(this).attr('data-id');
    $('input[name="policy"]').val(policy_id);
    $('#add-comment').dialog('open');
    return false;
  });
});
