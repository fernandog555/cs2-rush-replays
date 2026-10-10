// Valve serves replays over plain http, which Chrome flags as an insecure
// download. To avoid that warning, the replay is fetched inside the extension
// (offscreen document), turned into a blob: URL, and downloaded from there.
// If that fails, it falls back to downloading the original link directly.

const OFFSCREEN_URL = "offscreen.html";

async function ensureOffscreen() {
  const existing = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  if (existing.length) return;
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_URL,
    reasons: ["BLOBS"],
    justification: "Turn the fetched replay into a blob URL for chrome.downloads.",
  });
}

function waitForDownload(id) {
  return new Promise((resolve, reject) => {
    const listener = (delta) => {
      if (delta.id !== id || !delta.state) return;
      if (delta.state.current === "complete") {
        chrome.downloads.onChanged.removeListener(listener);
        resolve();
      } else if (delta.state.current === "interrupted") {
        chrome.downloads.onChanged.removeListener(listener);
        reject(new Error(delta.error?.current ?? "download interrupted"));
      }
    };
    chrome.downloads.onChanged.addListener(listener);
  });
}

async function download(url, filename) {
  const id = await chrome.downloads.download({ url, filename, conflictAction: "overwrite", saveAs: false });
  await waitForDownload(id);
}

async function downloadReplay(url, filename) {
  try {
    await ensureOffscreen();
    const res = await chrome.runtime.sendMessage({ type: "fetch-to-blob", url });
    if (!res?.ok) throw new Error(res?.error ?? "fetch failed");
    try {
      await download(res.blobUrl, filename);
    } finally {
      chrome.runtime.sendMessage({ type: "revoke-blob", blobUrl: res.blobUrl });
    }
  } catch (err) {
    console.warn("Blob download failed, falling back to direct link:", err);
    await download(url, filename);
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "download-replay") return;
  downloadReplay(msg.url, msg.filename)
    .then(() => sendResponse({ ok: true }))
    .catch((err) => sendResponse({ ok: false, error: String(err.message ?? err) }));
  return true; // keep the channel open for the async response
});
