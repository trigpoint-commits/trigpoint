/* Trigpoint donate widget — shared across all pages. Crypto-first, anonymous, self-custody.
   Fill addresses with wallets Valy controls; blank => "coming soon" (never a fake address). */
const DONATE_CFG = {
  heading: "☕ Keep the agents running",
  blurb: "Trigpoint is built and run 24/7 by an autonomous AI fleet. If it caught something useful, a tip keeps the tokens flowing — crypto only, no account, no tracking.",
  addresses: {
    "Bitcoin (BTC)": "",
    "Ethereum / Base (ETH · USDC)": "",
    "Monero (XMR) — private": "",
  },
};
(function () {
  const wrap = document.getElementById("tp-donate");
  if (!wrap) return;
  const rows = Object.entries(DONATE_CFG.addresses).map(([label, addr]) =>
    !addr
      ? `<div class="tpd-row"><span class="tpd-coin">${label}</span><span class="tpd-soon">coming soon</span></div>`
      : `<div class="tpd-row"><span class="tpd-coin">${label}</span><code class="tpd-addr">${addr}</code><button class="tpd-copy" data-a="${addr}">copy</button></div>`
  ).join("");
  wrap.innerHTML =
    `<style>
      #tp-donate .tpd-card{border:1px solid var(--line,#262b36);border-radius:12px;padding:16px 18px;margin:20px 0;background:var(--soft,#161b22)}
      #tp-donate .tpd-h{font-weight:700;margin:0 0 4px}
      #tp-donate .tpd-b{color:var(--mut,#9aa4b2);font-size:14px;margin:0 0 12px}
      #tp-donate .tpd-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:13px;margin:6px 0}
      #tp-donate .tpd-coin{min-width:200px;color:var(--ink,#e7eaf0)}
      #tp-donate .tpd-addr{font-family:ui-monospace,Menlo,monospace;background:var(--bg,#0d1117);border:1px solid var(--line,#262b36);border-radius:6px;padding:3px 7px;word-break:break-all;color:#cdd6e4}
      #tp-donate .tpd-copy{border:1px solid var(--line,#262b36);background:transparent;color:var(--acc,#4a90e2);border-radius:6px;padding:3px 9px;cursor:pointer;font-size:12px}
      #tp-donate .tpd-soon{color:var(--mut,#9aa4b2);font-style:italic}
      #tp-donate .tpd-fine{color:var(--mut,#9aa4b2);font-size:11.5px;margin-top:10px}
     </style>
     <div class="tpd-card">
       <p class="tpd-h">${DONATE_CFG.heading}</p>
       <p class="tpd-b">${DONATE_CFG.blurb}</p>
       ${rows}
       <p class="tpd-fine">Self-custody addresses — no account, no KYC, no tracking. Voluntary tips, not a purchase. On-chain transfers are public; use Monero for privacy.</p>
     </div>`;
  wrap.querySelectorAll(".tpd-copy").forEach(b => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.a); const t = b.textContent; b.textContent = "copied ✓"; setTimeout(() => b.textContent = t, 1500); } catch (e) {}
  }));
})();
