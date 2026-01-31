const API_BASE = "http://127.0.0.1:8000";

async function getVideoIdFromTab() {
  return new Promise(resolve => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      if (!tabs || !tabs[0]) {
        resolve(null);
        return;
      }

      chrome.tabs.sendMessage(
        tabs[0].id,
        { action: "GET_VIDEO_ID" },
        response => {
          resolve(response?.videoId || null);
        }
      );
    });
  });
}

// LOAD TRANSCRIPT / PROCESS VIDEO
document.getElementById("loadBtn").onclick = async () => {
  const status = document.getElementById("status");
  status.innerText = "Detecting video...";

  const videoId = await getVideoIdFromTab();

  if (!videoId) {
    status.innerText = "No video detected.";
    return;
  }

  status.innerText = "Processing transcript...";

  try {
    const res = await fetch(`${API_BASE}/process?video_id=${videoId}`);
    const data = await res.json();

    if (data.error) {
      status.innerText = "" + data.error;
    } else {
      status.innerText = `Transcript loaded (${data.chunks} chunks)`;
    }
  } catch (err) {
    status.innerText = "Backend not reachable.";
  }
};

// ASK QUESTION
document.getElementById("askBtn").onclick = async () => {
  const answerBox = document.getElementById("answer");
  const question = document.getElementById("question").value.trim();

  if (!question) {
    answerBox.innerText = "Please enter a question.";
    return;
  }

  answerBox.innerText = "Thinking...";

  const videoId = await getVideoIdFromTab();
  if (!videoId) {
    answerBox.innerText = "No video detected.";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, question })
    });

    const data = await res.json();
    answerBox.innerText = data.answer || data.error;

  } catch (err) {
    answerBox.innerText = "Backend not reachable.";
  }
};
