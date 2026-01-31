from fastapi import FastAPI
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from dotenv import load_dotenv
import os
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from fastapi.middleware.cors import CORSMiddleware


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

if not os.path.exists(VECTOR_DIR):
    os.makedirs(VECTOR_DIR)


# Pydantic Models
class AskRequest(BaseModel):
    video_id: str
    question: str


# STEP 1: PROCESS VIDEO
@app.get("/process")
def process_video(video_id: str):
    """
    Extract transcript → split → embed → FAISS → save to local storage
    """

    # 1. Fetch transcript (new method)
    try:
        fetched_transcript = YouTubeTranscriptApi().fetch(
            video_id,
            languages=["en"]   # add "hi" for Hindi auto-generated
        )

        transcript_list = fetched_transcript.to_raw_data()
        transcript = " ".join(chunk["text"] for chunk in transcript_list)

    except Exception as e:
        return {"error": f"Transcript fetch failed: {str(e)}"}

    # 2. Split text
    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
        chunks = splitter.create_documents([transcript])
    except Exception as e:
        return {"error": f"Splitter failed: {str(e)}"}

    # 3. Create embeddings + FAISS store
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
        vector_store = FAISS.from_documents(chunks, embeddings)

        faiss_path = f"{VECTOR_DIR}/{video_id}"
        vector_store.save_local(faiss_path)

        return {"message": "Indexing complete", "chunks": len(chunks)}

    except Exception as e:
        return {"error": f"Embedding/FAISS failed: {str(e)}"}


# STEP 2: ASK QUESTION (RAG)
@app.post("/ask")
def ask_question(req: AskRequest):
    video_id = req.video_id
    question = req.question

    faiss_path = f"{VECTOR_DIR}/{video_id}"

    if not os.path.exists(faiss_path):
        return {"error": "Video not processed yet. Click 'Load Transcript' first."}

    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
        vector_store = FAISS.load_local(
            faiss_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        return {"error": f"FAISS load failed: {str(e)}"}

    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    try:
        parallel_chain = RunnableParallel({
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough()
        })

        prompt = PromptTemplate(
            template="""
            You are a helpful assistant.
            Answer using ONLY the transcript context below.

            {context}

            Question: {question}
            """,
            input_variables=["context", "question"]
        )

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2
        )

        parser = StrOutputParser()

        rag_chain = parallel_chain | prompt | llm | parser

        answer = rag_chain.invoke(question)

        return {"answer": answer}

    except Exception as e:
        return {"error": f"RAG failed: {str(e)}"}

