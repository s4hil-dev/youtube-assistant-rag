from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from fastapi.middleware.cors import CORSMiddleware


# ---------------------------------------------------------
# INIT
# ---------------------------------------------------------
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VECTOR_DIR = "vectorstores"
os.makedirs(VECTOR_DIR, exist_ok=True)


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
class AskRequest(BaseModel):
    video_id: str
    question: str


# ---------------------------------------------------------
# PROCESS VIDEO → Summary → Chunk → Embed → FAISS
# ---------------------------------------------------------
@app.get("/process")
def process_video(video_id: str):
    """
    Extract transcript → Lightweight Summary → Chunk → Embed → FAISS.
    """

    # 1. Fetch transcript
    try:
        transcript_data = YouTubeTranscriptApi().fetch(
            video_id, languages=["en"]
        ).to_raw_data()

        transcript = " ".join(ch["text"] for ch in transcript_data)
    except Exception as e:
        return {"error": f"Transcript fetch failed: {str(e)}"}


    # 2. FAST Summary (use only first 20k chars)
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2
        )

        short_transcript = transcript[:20000]

        summary_prompt = f"""
        Summarize the following YouTube transcript (first 20k characters only)
        in 10–20 bullet points:

        {short_transcript}
        """

        summary_msg = llm.invoke(summary_prompt)
        summary = summary_msg.content if hasattr(summary_msg, "content") else str(summary_msg)

    except Exception as e:
        return {"error": f"Summarization failed: {str(e)}"}


    # 3. Save transcript + summary
    transcript_path = f"{VECTOR_DIR}/{video_id}_transcript.txt"
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(f"SUMMARY:\n{summary}\n\nFULL TRANSCRIPT:\n{transcript}")


    # 4. Chunk ONLY the transcript (NOT summary)
    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=40)
        chunks = splitter.create_documents([transcript])
    except Exception as e:
        return {"error": f"Chunking failed: {str(e)}"}


    # 5. Embed + FAISS
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
        store = FAISS.from_documents(chunks, embeddings)
        store.save_local(f"{VECTOR_DIR}/{video_id}")

        return {
            "message": "Processing complete (optimized)",
            "chunks": len(chunks),
            "summary": summary
        }

    except Exception as e:
        return {"error": f"Embedding/FAISS failed: {str(e)}"}



@app.post("/ask")
def ask_question(req: AskRequest):
    video_id = req.video_id
    question = req.question.strip().lower()

    faiss_path = f"{VECTOR_DIR}/{video_id}"
    transcript_path = f"{VECTOR_DIR}/{video_id}_transcript.txt"

    if not os.path.exists(faiss_path):
        return {"error": "Video not processed. Click 'Load Transcript' first."}

    # --- Load summary ---
    summary_file = f"{VECTOR_DIR}/{video_id}_summary.txt"
    summary = None

    if os.path.exists(summary_file):
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = f.read()
    else:
        # fallback: read summary from transcript file
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw = f.read()
            if raw.startswith("SUMMARY:"):
                summary = raw.split("SUMMARY:")[1].split("FULL TRANSCRIPT:")[0].strip()

    # --- Detect global questions ---
    global_keywords = [
        "summary", "summarize", "overall", "main idea",
        "key points", "explain", "explain like", "overview",
        "gist", "in short", "high level"
    ]

    is_global = any(k in question for k in global_keywords)

    # If global → return cleaned summary instantly
    if is_global:
        return {
            "answer": summary,
            "mode": "summary-mode"
        }

    # --- For local questions: RAG retrieval ---
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
        store = FAISS.load_local(
            faiss_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        return {"error": f"FAISS load failed: {str(e)}"}

    retriever = store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Build smart chain
    try:
        chain_inputs = RunnableParallel({
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
            "summary": lambda _: summary
        })

        prompt = PromptTemplate(
            template="""
                You are a YouTube video assistant with BOTH:
                1. A global summary of the entire video
                2. Local transcript chunks retrieved using FAISS
                
                Rules:
                - If the question asks about specific details, use transcript context.
                - Always consult summary for extra clarity.
                - Never hallucinate. Only use provided info.
                - Keep answers clear and clean.
                
                --------------------
                GLOBAL SUMMARY:
                {summary}
                
                --------------------
                LOCAL CONTEXT:
                {context}
                
                --------------------
                QUESTION:
                {question}
                
                Your answer:
                """,
            input_variables=["context", "question", "summary"]
        )

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2
        )

        parser = StrOutputParser()

        rag_chain = chain_inputs | prompt | llm | parser
        answer = rag_chain.invoke(question)

        return {
            "answer": answer,
            "mode": "rag-mode"
        }

    except Exception as e:
        return {"error": f"RAG failed: {str(e)}"}


