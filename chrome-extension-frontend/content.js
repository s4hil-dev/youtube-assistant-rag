function getYouTubeVideoId() {
  try {
    const url = new URL(window.location.href);
    return url.searchParams.get("v");
  } catch {
    return null;
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "GET_VIDEO_ID") {
    const videoId = getYouTubeVideoId();
    sendResponse({ videoId });
  }
});
