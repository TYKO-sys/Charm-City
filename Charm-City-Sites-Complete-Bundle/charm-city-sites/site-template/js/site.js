/* Charm City Sites — template behavior
   1. Quote form submits in the background (visitor never leaves the page).
   2. Sticky call bar appears on small screens after scrolling.
   No frameworks, no dependencies, nothing to break. */
(function () {
  "use strict";

  var form = document.getElementById("quote");
  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var honeypot = form.querySelector('[name="_honey"]');
      if (honeypot && honeypot.value) { return; } /* bot, ignore silently */
      var action = form.getAttribute("action") || "";
      var ajax = action.replace("formsubmit.co/", "formsubmit.co/ajax/");
      var data = {};
      new FormData(form).forEach(function (v, k) { if (k !== "_honey") { data[k] = v; } });
      var btn = form.querySelector('button[type="submit"]');
      if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }
      fetch(ajax, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(data)
      })
        .then(function (r) { return r.ok ? Promise.resolve() : Promise.reject(new Error("status " + r.status)); })
        .then(function () {
          form.innerHTML =
            '<div class="form-ok"><strong>Got it — we got your request.</strong>' +
            "We usually call back within the hour. If water is actively pouring, " +
            'call us directly at the number on this page.</div>';
        })
        .catch(function () {
          /* AJAX failed: fall back to a normal browser submit so the lead is never lost. */
          form.removeEventListener("submit", arguments.callee);
          form.submit();
        });
    });
  }

  var bar = document.getElementById("callbar");
  if (bar) {
    var flip = function () {
      if (window.scrollY > 260) { bar.classList.add("on"); }
      else { bar.classList.remove("on"); }
    };
    window.addEventListener("scroll", flip, { passive: true });
    flip();
  }
})();
