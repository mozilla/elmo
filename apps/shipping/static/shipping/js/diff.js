/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(document).ready(function() {
  $('.ui-accordion-header').click(function(e) {
    $(this).each(function(i) {
      $(this).children('.ui-icon')
        .toggleClass('ui-icon-triangle-1-s')
        .toggleClass('ui-icon-triangle-1-e');
    }).next().toggle();
  });
});
