// Runs on your Steam match history page. It only acts when the URL ends in
// #autodownload (which the Python script adds), so browsing the page normally
// never triggers a download.
(() => {
  if (location.hash !== "#autodownload") return;

  const banner = document.createElement("div");
  banner.style.cssText =
    "position:fixed;top:12px;right:12px;z-index:99999;padding:10px 14px;" +
    "background:#1b2838;color:#c7d5e0;border:1px solid #66c0f4;border-radius:4px;" +
    "font:14px Arial,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.5)";
  const show = (text) => {
    banner.textContent = `Rush replay: ${text}`;
    if (!banner.isConnected) document.body.appendChild(banner);
  };

  // The first replay link on the page is the most recent match.
  const link = document.querySelector("a[href*='.dem.bz2']");
  if (!link) {
    show("no 'Download GOTV Replay' link found (not signed in, no matches, or replays expired).");
    return;
  }

  // Drop the flag so a page refresh doesn't download again.
  history.replaceState(null, "", location.pathname + location.search);

  const url = link.href;
  const filename = url.split("/").pop();
  show(`downloading ${filename}...`);
  chrome.runtime.sendMessage({ type: "download-replay", url, filename }, (res) => {
    if (chrome.runtime.lastError) show(`failed: ${chrome.runtime.lastError.message}`);
    else if (res?.ok) show(`saved ${filename} to Downloads.`);
    else show(`failed: ${res?.error ?? "unknown error"}`);
  });
})();
