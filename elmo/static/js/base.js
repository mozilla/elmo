/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var gLogoutHelper = (function() {
    class LogoutHelper {
        constructor(container) {
            this.container = container;
            fetch(document.head.querySelector('link[rel=user_json]').href)
            .then(
                response => response.json()
            )
            .then(
                res => this.showUser(res)
            )
            this.get('a.site_logout').onclick = (e => {
                this.show();
                e.stopPropagation();
                return false;
            });
            this.get('.logout .button').onclick = function() {
                window.location = this.dataset.href;
                return false;
            }

            // If Esc pressed or clicked outside popup, close it
            document.addEventListener("keyup", e => {
                if (e.keyCode == 27) {
                    this.hide();
                }
            });
            document.body.addEventListener("click", () => this.hide());
        }

        get(selector) {
            return this.container.querySelector(selector);
        }

        showUser(data) {
            if (data.user_name) {
                this.get('.username').textContent = data.user_name;
                this.container.classList.add('user');
            }
            else {
                this.container.classList.remove('user');
            }
        }

        show() {
            this.container.classList.add('logout');
        }

        hide () {
            this.container.classList.remove('logout');
        }
    }

    return new LogoutHelper(document.getElementById("auth"));
})();
