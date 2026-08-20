/**
 * AI YouTube Lecture Notes - Background Service Worker (Manifest V3)
 */

chrome.runtime.onInstalled.addListener(async () => {
  console.log("AI YouTube Lecture Notes extension installed.");

  // Set default settings if not configured
  const existing = await chrome.storage.local.get(["apiUrl", "modelName"]);
  if (!existing.apiUrl) {
    await chrome.storage.local.set({
      apiUrl: "http://127.0.0.1:8000/api/v1",
      modelName: "gemini-2.5-flash"
    });
  }
});

// Message forwarding router
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "GET_ACTIVE_TAB_VIDEO") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        sendResponse({ tab: tabs[0] });
      } else {
        sendResponse({ tab: null });
      }
    });
    return true; // Keep channel open for async response
  }
});
