class SignoffWatcher {
  constructor(row, button, csrf) {
    this.row = row;
    this.button = button;
    this.csrf = csrf;
  }
  async post() {
    const url = new URL(this.button.form.action);
    url.searchParams.set("action", this.button.name);
    this.row.lastElementChild.innerHTML="processing...";
    let response = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": this.csrf,
      }
    });
    let code = response.ok;
    if (!response.ok) {
      this.row.lastElementChild.innerHTML="bad things happened";
      return;
    }
    let rv = await response.json();
    this.row.remove();
  }
}

function signoff(e) {
  console.log(e.originalTarget);
  e.preventDefault();
  let csrf_token = document.querySelector('input[name=csrfmiddlewaretoken]').value;
  let row = e.originalTarget;
  while (row.nodeName !== 'TR') {
    row = row.parentElement;
  }
  row.parentElement.appendChild(row);
  let sow = new SignoffWatcher(row, e.originalTarget, csrf_token);
  sow.post();
}

Array.from(document.querySelectorAll(".add-signoff > button"))
  .forEach(b => b.onclick = signoff);
