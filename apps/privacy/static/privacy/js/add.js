/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

class PolicyObserver {
  constructor() {
    this.elements = document.forms.editor.elements;
    this.submit = document.forms.editor.querySelector('input[type=submit]');
    this.preview = document.getElementById("policy");
    this.waiting = null;
    this.elements.comment.addEventListener(
      'keyup', e => this.willValidate()
    );
  }

  onContentEdit(keydown) {
    this.waiting = setTimeout(e => this.render(e), 1000);
  }

  willValidate() {
    setTimeout(e => this.validate(e), 200);
  }

  render() {
    this.waiting = null;
    this.preview.innerHTML = this.elements.content.value;
    this.elements.content.addEventListener(
      'keydown',
      e => this.onContentEdit(e),
      {once: true}
    );
    this.willValidate();
  }

  validate() {
    let ok =
      this.waiting === null
      && this.elements.comment.value
      && this.elements.content.value !== this.elements.content.textContent;
    this.submit.disabled = !ok;
  }
}

let policyObserver = new PolicyObserver();
policyObserver.render();
