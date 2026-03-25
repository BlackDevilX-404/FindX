import os
from typing import Optional, List

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, field_validator

try:
    from .pdf_chroma_ingest import ChromaMultimodalDB
except ImportError:
    from pdf_chroma_ingest import ChromaMultimodalDB


class PdfSearchInput(BaseModel):
    question: str = Field(..., description="The specific question or keyword to search in the PDF database.")
    top_k: int = Field(
        default=3,
        ge=1,
        le=8,
        description="How many vector results to fetch from the PDF store.",
    )

    @field_validator("top_k", mode="before")
    @classmethod
    def coerce_top_k(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.isdigit():
                return int(value)
        return value


class QueryOrchestrator:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"): # Updated to current Groq model string
        load_dotenv() # By default, looks for .env in current working directory

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing. Add it to your .env file.")

        self.llm = ChatGroq(
            model=model_name,
            temperature=0, # Keep at 0 for strict tool calling
            groq_api_key=api_key,
        )
        print(f"[Orchestrator] Groq model ready: {model_name}")
        self.system_prompt = (
            "You are an intelligent enterprise search assistant.\n"
            "1) If the answer requires company documents, ALWAYS call `pdf_vector_search`.\n"
            "2) If the user makes a greeting or asks a general knowledge question, answer directly without tools.\n"
            "3) If tool results are empty, state clearly that you could not find relevant company context.\n"
            "4) Base your final answer ONLY on the tool observations. Do not hallucinate company policies."
        )

    def _build_pdf_search_tool(self, chat_id: str, doc_uuid: Optional[str] = None):
        @tool("pdf_vector_search", args_schema=PdfSearchInput)
        def pdf_vector_search(question: str, top_k: int | str = 3) -> str:
            """
            Search ingested PDF chunks from Chroma DB.
            Use this tool FIRST when the user asks about company policies, documents, or guidelines.
            """
            if isinstance(top_k, str):
                top_k = int(top_k.strip()) if top_k.strip().isdigit() else 3

            top_k = max(1, min(int(top_k), 8))
            print(f"[Orchestrator] Tool call started: pdf_vector_search | top_k={top_k}")
            db = ChromaMultimodalDB(chat_id=chat_id, doc_uuid=doc_uuid)
            grouped = db.query_grouped(question=question, top_k=top_k, only_doc=doc_uuid)

            if not grouped:
                print("[Orchestrator] Retrieval returned no relevant chunks.")
                return "Observation: No relevant PDF content found for this query."

            print("[Orchestrator] Retrieved successfully, sending for generation.")
            lines = []
            for current_doc_uuid, chunks in grouped.items():
                lines.append(f"[doc_uuid={current_doc_uuid}]")
                for idx, chunk in enumerate(chunks, start=1):
                    lines.append(f"{idx}. {chunk}")
            return "\n".join(lines)

        return pdf_vector_search

    def _build_agent(self, chat_id: str, doc_uuid: Optional[str] = None):
        tools = [self._build_pdf_search_tool(chat_id=chat_id, doc_uuid=doc_uuid)]
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=self.system_prompt,
            debug=True,
        )

    @staticmethod
    def _extract_answer(messages: List[BaseMessage]) -> str:
        for message in reversed(messages):
            if not isinstance(message, AIMessage):
                continue

            content = message.content
            if isinstance(content, str):
                return content

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                if text_parts:
                    return "\n".join(part for part in text_parts if part)

        raise ValueError("Agent did not return a final text response.")

    def answer(self, user_query: str, chat_id: str, doc_uuid: Optional[str] = None, chat_history: List[BaseMessage] = None) -> str:
        """
        Pass chat_history (list of HumanMessage/AIMessage) from your frontend/DB if you want conversational memory.
        """
        if chat_history is None:
            chat_history = []
            
        print("[Orchestrator] Building agent...")
        agent = self._build_agent(chat_id=chat_id, doc_uuid=doc_uuid)
        print("[Orchestrator] Agent ready. Starting retrieval and generation...")
        result = agent.invoke(
            {
                "messages": [
                    *chat_history,
                    HumanMessage(content=user_query),
                ]
            }
        )

        print("[Orchestrator] Generation completed successfully.")
        return self._extract_answer(result["messages"])


if __name__ == "__main__":
    orchestrator = QueryOrchestrator()
    sample_chat_id = "demo_chat"
    sample_doc_uuid = None
    
    # Simple list to hold memory during the CLI test
    memory = []

    print("Type your question (Ctrl+C to stop):")
    while True:
        try:
            user_q = input("> ").strip()
            if not user_q:
                continue
                
            answer = orchestrator.answer(
                user_query=user_q,
                chat_id=sample_chat_id,
                doc_uuid=sample_doc_uuid,
                chat_history=memory # Pass the memory in
            )
            print(f"\n{answer}\n")
            
            # (Optional) In a real app, your database handles appending Human and AI messages to memory here
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
