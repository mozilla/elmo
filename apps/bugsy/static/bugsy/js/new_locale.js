/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function getBugURL(params) {
  var ps = [];
  for (var k in params) {
    if (k != 'title') {
      ps.push(k + '=' + encodeURIComponent(params[k]));
    }
  }
  var url = 'https://bugzilla.mozilla.org/enter_bug.cgi?';
  url += ps.join('&');
  return url;
}

function doBugs() {
  var params = {};
  function addParam() {
    params[this.name] = this.value;
  }
  $.each(document.forms.bugdata.elements, addParam);
  function handleLinkJSON(data, result) {
    var out = $('#links');
    if (result != 'success') {
      out.html('Failed to create bug links');
      return;
    }
    out.html('');
    $.each(data, function() {
      var child = $('<a>').text(this.title);
      child.attr('href', getBugURL(this));
      child.attr('target', '_blank');
      out.append(child);
      out.append(' ');
    });
  }
  $.getJSON(NEW_LOCALE_URL, params, handleLinkJSON);
}
