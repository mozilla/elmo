/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
         }).error(function(jqXHR, textStatus, errorThrown) {
           $('form.site_login').hide();
           $('a.site_login').hide();
           $('.site_login_error').show();
           $('.site_login_error code').text(errorThrown);
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
