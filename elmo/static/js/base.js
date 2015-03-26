/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

if (!CONFIG) alert('variable CONFIG must be loaded first');

var AjaxLogin = (function() {
  var container = $('#auth');
  return {
     initialize: function() {
       /* Do a light-weight AJAX GET for the username;
        * or else prepare the login form with a fresh csrf token.
        */
       $.getJSON(CONFIG.USER_URL, function(res) {
         if (res.user_name) {
           $('a.site_login', container).hide();
           $('.username', container).text(res.user_name);
           $('.site_logout', container).show();
         } else {
           if ($('input[name="csrfmiddlewaretoken"]', container).size() != 1) {
             $('<input type="hidden">')
               .attr('name', 'csrfmiddlewaretoken')
               .appendTo($('<div>')
                           .hide()
                           .prependTo($('form', container)));
           }
           $('input[name="csrfmiddlewaretoken"]', container)
             .val(res.csrf_token);
         }
       });

       /* Initially a 'Log in' link appears on every page */
       $('a.site_login', container).click(function() {
         AjaxLogin.show_login_form();
         return false;
       });

       /* Show menu when username clicked */
       $('a.site_logout', container).click(function() {
         AjaxLogin.show_logout_form();
         return false;
       });

       /* Show menu when username clicked */
       $('.logout .button', container).click(function() {
         window.location = $(this).data('href');
         return false;
       });

       /* Keep a live event delegator on the login form because if a login
        * attempt fails it will return us the HTML of the failed form which
        * we'll use to replace the old one.
        */
       $('form', container).live('submit', function() {
         var p = {};
         $.each($(this).serializeArray(), function(i, o) {
           p[o.name] = o.value;
         });

         $('form .login', container)
           .append($('<img>', {src: CONFIG.LOADING_GIF_URL}));

         $.post($(this).attr('action'), p, function(res) {
           if (res.user_name) {
             if (CONFIG.NEEDS_RELOAD) {
               location.href = CONFIG.CURRENT_URL;
             } else {
               $('form', container).hide();
               $('a.site_login', container).hide();
               $('.username', container).text(res.user_name);
               $('.site_logout', container).show();
             }
           } else {
             // if it failed we get the whole form as HTML
             $('form', container).remove();
             // re-insert it into the page
             $('#auth').append(res);
             // remove errors once the user starts correcting themselves
             if ($('form label span.error', container).size()) {
               $('form input', container).focus(function() {
                 $('form input', container).unbind('focus');
                 $('form label span.error', container).fadeOut(500);
               });
             }
           }
         }).error(function(jqXHR, textStatus, errorThrown) {
           $('form.site_login > .login > *:not(".site_login_error")').hide();
           $('.site_login_error').show();
           $('.site_login_error code').text(errorThrown);
         });
         return false;
       });
     },
    show_login_form: function() {
      $('form', container).toggle();
      $('#id_username').trigger('focus');
    },
    show_logout_form: function() {
      $('section.login', container).hide();
      $('section.logout', container).show();
      $('form', container).toggle();
    }
  };
})();


$(function() {
  AjaxLogin.initialize();
  if (location.hash == '#login') {
    AjaxLogin.show_login_form();
  }

  function closePopup() {
    $('#auth form').hide();
  }

  // If Esc pressed or clicked outside popup, close it
  $(document).keyup(function(e) {
    if (e.keyCode == 27) {
      closePopup();
    }
  });
  $('body').live("click", function() {
    closePopup();
  });
  $('#auth form').live("click", function(e) {
    e.stopPropagation();
  });
});
