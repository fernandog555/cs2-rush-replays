// Fetches the replay and hands back a blob: URL the service worker can download.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "fetch-to-blob") {
    fetch(msg.url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} (Valve keeps replays ~30 days)`);
        return r.blob();
      })
      .then((blob) => sendResponse({ ok: true, blobUrl: URL.createObjectURL(blob) }))
      .catch((err) => sendResponse({ ok: false, error: String(err.message ?? err) }));
    return true;
  }
  if (msg.type === "revoke-blob") {
    // Give Chrome a moment to finish reading the blob before freeing it.
    setTimeout(() => URL.revokeObjectURL(msg.blobUrl), 60_000);
  }
});
