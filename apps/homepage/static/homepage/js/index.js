/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(function() {
  $("select").chosen({
    width: "260px",
    no_results_text: "No teams match"
  }).change(function() {
    window.location = '/teams/' + $(this).val();
  });
});
