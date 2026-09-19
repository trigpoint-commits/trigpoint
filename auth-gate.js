/* Trigpoint soft access gate — user+password overlay for controlled preview testing.
   NOTE: this is a CLIENT-SIDE (soft) gate for a static site: it keeps casual visitors and search engines out during
   testing, but the page source is still technically viewable to a determined user. For hard protection, front the
   site with Cloudflare Access (as the casavaida board does). Adequate for gated preview + tester access.
   Credential = SHA-256(user + "\n" + password). Change CRED_HASH to rotate. Temp creds are handed over out-of-band. */
(function () {
  var CRED_HASH = "5c64e01db60f49adeb84288044e4de957604b4ff948db72a88d148a85897ee88";
  if (sessionStorage.getItem("tp_gate_ok") === "1") return;
  // hide the real page until unlocked
  var root = document.documentElement;
  root.style.visibility = "hidden";
  async function sha256(s) {
    var b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
    return Array.from(new Uint8Array(b)).map(function (x) { return x.toString(16).padStart(2, "0"); }).join("");
  }
  function build() {
    var ov = document.createElement("div");
    ov.setAttribute("style",
      "position:fixed;inset:0;z-index:99999;background:#0b0b0c;color:#f4f4f2;display:flex;align-items:center;" +
      "justify-content:center;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;visibility:visible");
    ov.innerHTML =
      '<form id="tpg" style="width:320px;max-width:88vw;text-align:left">' +
      '<div style="font-weight:800;font-size:20px;letter-spacing:-.02em;margin-bottom:6px">Trigpoint — private preview</div>' +
      '<div style="color:#8a8a86;font-size:13px;margin-bottom:18px">Enter the preview credentials to continue.</div>' +
      '<input id="tpu" placeholder="user" autocomplete="off" style="width:100%;padding:12px;margin-bottom:10px;background:#141414;border:1px solid #33332f;color:#f4f4f2;border-radius:8px;font-size:15px">' +
      '<input id="tpp" type="password" placeholder="password" style="width:100%;padding:12px;margin-bottom:14px;background:#141414;border:1px solid #33332f;color:#f4f4f2;border-radius:8px;font-size:15px">' +
      '<button type="submit" style="width:100%;padding:12px;background:#d7ff3f;color:#000;border:0;border-radius:8px;font-weight:800;font-size:15px;cursor:pointer">Enter</button>' +
      '<div id="tpm" style="color:#ff5c5c;font-size:13px;margin-top:10px;min-height:16px"></div></form>';
    document.body.appendChild(ov);
    root.style.visibility = "visible";        // reveal the overlay (page behind stays covered)
    document.getElementById("tpu").focus();
    document.getElementById("tpg").addEventListener("submit", async function (e) {
      e.preventDefault();
      var u = document.getElementById("tpu").value.trim();
      var p = document.getElementById("tpp").value;
      var h = await sha256(u + "\n" + p);
      if (h === CRED_HASH) {
        sessionStorage.setItem("tp_gate_ok", "1");
        ov.remove();
      } else {
        document.getElementById("tpm").textContent = "Incorrect — check the credentials you were given.";
      }
    });
  }
  if (document.body) build();
  else window.addEventListener("DOMContentLoaded", build);
})();
