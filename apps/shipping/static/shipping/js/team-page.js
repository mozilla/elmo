/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$(function() {
    // make header stick to the top
    $('.trees').stickyTableHeaders();
    // make the scroll tops of our application anchors show below the header
    // shift down by offsetTop and header height
    var off = $('.trees > thead').height() +
              document.querySelector('.appname h3').offsetTop;
    off += 'px';
    $('.appname h3').css({'padding-top': off, 'margin-top': '-' + off});
});
