# 🎥 YouTube RAG Assistant (FastAPI + Chrome Extension)

A lightweight Chrome Extension that lets you **ask questions about any
YouTube video** using **RAG (Retrieval Augmented Generation)** powered
by **Gemini + LangChain**.

The extension extracts the video transcript, embeds it using FAISS, and
performs semantic search to give accurate, context-aware answers --- all
running locally with your backend.

------------------------------------------------------------------------

## 🚀 Features

-   🔍 One-click **Load Transcript** from any YouTube video\
-   🤖 Ask natural language questions about the video\
-   🧠 Uses **Google Gemini**, **FAISS**, and **LangChain**\
-   ⚡ Runs locally with a FastAPI backend\
-   🎨 Clean, modern UI\
-   🧩 Auto-detects video ID from current YouTube tab\
-   🔒 No third-party servers --- your data stays on your machine

------------------------------------------------------------------------

## 📂 Folder Structure

    youtube-rag-assistant/
    │
    ├── backend/
    │   ├── main.py
    │   ├── vectorstores/
    │   ├── .env
    │   └── requirements.txt
    │
    └── extension/
        ├── manifest.json
        ├── popup.html
        ├── popup.js
        ├── popup.css
        ├── content.js
        ├── background.js
        └── icon.png

------------------------------------------------------------------------

## 🛠️ Backend Setup (FastAPI + Gemini)

### **1️⃣ Install dependencies**

Inside the `backend/` folder:

``` bash
pip install -r requirements.txt
```

If you don't have `requirements.txt`, create it using:

``` txt
fastapi
uvicorn
python-dotenv
youtube-transcript-api
langchain-google-genai
langchain-community
langchain-text-splitters
faiss-cpu
```

------------------------------------------------------------------------

### **2️⃣ Add your Gemini API Key**

Create a `.env` file:

    GOOGLE_API_KEY=YOUR_API_KEY_HERE

------------------------------------------------------------------------

### **3️⃣ Run the backend**

``` bash
uvicorn main:app --reload --port 8000
```

Backend starts at:

👉 http://127.0.0.1:8000\
👉 API docs: http://127.0.0.1:8000/docs

------------------------------------------------------------------------

## 🧩 Chrome Extension Setup

### **1️⃣ Load the extension**

1.  Open Chrome\
2.  Visit: `chrome://extensions/`\
3.  Enable **Developer Mode**\
4.  Click **Load unpacked**\
5.  Select the `extension/` folder

Your extension icon will appear in the Chrome toolbar.

------------------------------------------------------------------------

### **2️⃣ How to use**

1.  Open any YouTube video (`youtube.com/watch`)\
2.  Click the extension icon\
3.  Click **Load Transcript**\
4.  Enter your question\
5.  Click **Ask**\
6.  Get a RAG-powered answer instantly 🎉

------------------------------------------------------------------------

## 📡 API Endpoints

### **➡️ Process Transcript**

``` http
GET /process?video_id=VIDEO_ID
```

Extracts transcript → splits → embeds → stores FAISS index.

------------------------------------------------------------------------

### **➡️ Ask a Question**

``` http
POST /ask
{
  "video_id": "VIDEO_ID",
  "question": "Your question"
}
```

RAG pipeline: Transcript → FAISS search → Gemini → Answer.

------------------------------------------------------------------------

## 🧰 Tech Stack

### **Backend**

-   FastAPI\
-   FAISS\
-   LangChain\
-   Gemini (Google Generative AI)\
-   YouTube Transcript API

### **Extension**

-   Chrome Manifest V3\
-   JavaScript\
-   HTML + CSS\
-   Content Scripts\
-   Message Passing

------------------------------------------------------------------------

## 🔮 Future Improvements

-   🎨 Floating AI button on YouTube page\
-   📝 Markdown-rendered answers\
-   🧠 Summaries, chapters, keywords extraction\
-   ⚡ Cache indexes to avoid reprocessing\
-   🌙 Light / Dark mode auto detection\
-   📌 Pin answers to video timeline

------------------------------------------------------------------------

## 🤝 Contributing

Pull requests are welcome!\
For major changes, open an issue first to discuss what you'd like to
change.

------------------------------------------------------------------------

## 📜 License

MIT License © 2026

------------------------------------------------------------------------

Made with ❤️ by Sahil Ahmed
