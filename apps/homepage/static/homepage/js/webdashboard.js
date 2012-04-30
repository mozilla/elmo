/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/* This code depends on two global variables being defined:
   * LOCALE_CODE
   * WEBDASHBOARD_URL
 */

var WebdashboardRSSPuller = (function(code, webdashboard_url) {
  var URL = webdashboard_url + '?rss=1&locale=' + code;
  var parent = $('#webdashboard');

  function render(response) {
    $('.failed:visible', parent).hide();
    $('table:visible', parent).hide();

    var tbody = $('<tbody>');
    $.each(response.getElementsByTagName('item'), function() {
      var tr = $('<tr>').addClass('treesummary');
      var item = $(this);
      var title = $('title', item).text();
      var description = $('description', item).text();
      var link = $('link', item).text();
      $('<a>')
        .attr('href', link)
        .attr('title', description)
        .text(title)
        .appendTo($('<td>').appendTo(tr));

      tbody.append(tr);

    });
    tbody.appendTo($('table', parent));
    $('.loading:visible', parent).hide();
    $('table:hidden', parent).fadeIn(400);

  }

  function excuse_error() {
    $('.loading', parent).hide();
    $('table', parent).hide();
    $('p.intro, p.rss-icon-outer', parent).hide();
    $('.failed', parent).show();
  }

  function excuse_not_found() {
    $('.loading', parent).hide();
    $('table', parent).hide();
    $('p.intro, p.rss-icon-outer', parent).hide();
    $('.not-found', parent).show();
  }

  return {
     pull: function() {
      $.ajax({
        url: URL,
        success: render,
        error: function(jqXHR) {
          if (jqXHR.status == 404) {
            excuse_not_found();
          } else {
            // any other error
            excuse_error();
          }
        }
      });
     }
  };

})(LOCALE_CODE, WEBDASHBOARD_URL);


$(function() {
  WebdashboardRSSPuller.pull();
});
