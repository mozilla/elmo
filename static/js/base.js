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
 * The Original Code is l10n django site.
 *
 * The Initial Developer of the Original Code is
 *   Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Peter Bengtsson <peterbe@mozilla.com>
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

if (!CONFIG) alert('variable CONFIG must be loaded first');

var AjaxLogin = (function() {
  return {
     initialize: function() {
       /* Do a light-weight AJAX GET for the username;
        * or else prepare the login form with a fresh csrf token.
        */
       $.getJSON(CONFIG.USER_URL, function(res) {
         if (res.user_name) {
           $('a.site_login').hide();
           $('div.site_logout .username').text(res.user_name);
           $('div.site_logout').show();
         } else {
           $('input[name="csrfmiddlewaretoken"]', 'form.site_login')
             .val(res.csrf_token);
         }
       });


       /* Initially a 'Log in' link appears on every page */
       $('a.site_login').click(function() {
         AjaxLogin.show_login_form();
         return false;
       });

       /* Keep a live event delegator on the login form because if a login
        * attempt fails it will return us the HTML of the failed form which
        * we'll use to replace the old one.
        */
       $('form.site_login').live('submit', function() {
         var p = {};
         $.each($(this).serializeArray(), function(i, o) {
           p[o.name] = o.value;
         });

         $('form.site_login')
           .empty()
             .append($('<img>', {src: CONFIG.LOADING_GIF_URL}));

         $.post($(this).attr('action'), p, function(res) {
           if (res.user_name) {
             if (CONFIG.NEEDS_RELOAD) {
               location.href = CONFIG.CURRENT_URL;
             } else {
               $('form.site_login').hide();
               $('a.site_login').hide();
               $('div.site_logout .username').text(res.user_name);
               $('div.site_logout').show();
             }
           } else {
             // if it failed we get the whole form as HTML
             $('form.site_login').remove();
             // re-insert it into the page
             $('#auth').append(res);
             // remove errors once the user starts correcting themselves
             if ($('form.site_login label span.error').size()) {
               $('form.site_login input').focus(function() {
                 $('form.site_login input').unbind('focus');
                 $('form.site_login label span.error').fadeOut(500);
               });
             }
           }
         });
         return false;
       });
     },
    show_login_form: function() {
      $('a.site_login').hide();
      $('form.site_login').show();
      $('#id_username').trigger('focus');
    }
  };
})();


$(function() {
  AjaxLogin.initialize();
  if (location.hash == '#login') {
    AjaxLogin.show_login_form();
  }
});
