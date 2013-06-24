/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var styleRule = false;
function searchFor(s) {
  if (styleRule) {
    document.styleSheets[1].deleteRule(0);
    styleRule = false;
  }
  if (typeof s === 'string' && s.length) {
    var ruletxt = '#teams>li:not([class*=' +
      s.toLowerCase() + ']){display:none}';
    try {
      document.styleSheets[1].insertRule(ruletxt, 0);
      styleRule = true;
    } catch (e) {
      'catch';
    }
  }
}

$(function() {
  $('#id_locale_code').bind('keyup', function() {
    searchFor(this.value);
  });
});
