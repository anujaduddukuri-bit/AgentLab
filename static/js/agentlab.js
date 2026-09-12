(function () {
  function showWorking() {
    var overlay = document.getElementById("agent-working");
    if (!overlay) {
      return;
    }
    overlay.hidden = false;
    overlay.setAttribute("aria-busy", "true");
  }

  document.addEventListener("keydown", function (event) {
    var target = event.target;
    if (!target || !target.classList || !target.classList.contains("js-prompt")) {
      return;
    }
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    var form = target.form || target.closest("form");
    if (form) {
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
      } else {
        form.submit();
      }
    }
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || !form.classList.contains("js-agent-form")) {
      return;
    }
    showWorking();
    var button = form.querySelector("[type=submit]");
    if (button) {
      button.disabled = true;
      button.textContent = "Working…";
    }
  });
})();
