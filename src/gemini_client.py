# gemini_client.py - Работа с Google Gemini AI
import json
import traceback
from typing import List, Generator

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.config import GEMINI_API_KEY, GEMINI_MODEL_NAME, EMBEDDING_MODEL


# --- Инициализация клиента ---
client = None
GEMINI_CONFIGURED = False

try:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY не установлен")
    client = genai.Client()
    print(f"INFO: Gemini клиент инициализирован. Модель: {GEMINI_MODEL_NAME}")
    GEMINI_CONFIGURED = True
except Exception as e:
    print(f"ОШИБКА: Не удалось инициализировать Gemini: {e}")
    traceback.print_exc()


# --- Pydantic схемы ---
class DocumentRoute(BaseModel):
    doc_id: str
    reason: str


class DocumentRouterResponse(BaseModel):
    relevant_documents: List[DocumentRoute]


class RagDecision(BaseModel):
    requires_new_search: bool = Field(
        description="Set to true if the user asks a new, distinct question."
    )
    reason: str = Field(description="A brief explanation for the decision.")


# --- Функции ---
def stream_response(history: List[dict], system_prompt: str) -> Generator[str, None, None]:
    """Стриминг ответа от Gemini"""
    if not client:
        yield f"data: {json.dumps({'type': 'error', 'data': 'Gemini не инициализирован'})}\n\n"
        return

    contents = [{'role': msg['role'], 'parts': [{'text': msg['content']}]} for msg in history]

    try:
        stream = client.models.generate_content_stream(
            model=GEMINI_MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
                max_output_tokens=8192
            )
        )
        for chunk in stream:
            if chunk.text:
                yield f"data: {json.dumps({'type': 'content', 'data': chunk.text})}\n\n"
    except Exception as e:
        print(f"Ошибка Gemini API: {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'error', 'data': f'Ошибка API: {e}'})}\n\n"


def generate_json(prompt: str, schema: type[BaseModel], temperature: float = 0.0):
    """Генерация структурированного JSON ответа"""
    if not client:
        return None

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
                "temperature": temperature
            }
        )
        if hasattr(response, 'parsed') and response.parsed:
            return response.parsed
        return None
    except Exception as e:
        print(f"Ошибка генерации JSON: {e}")
        traceback.print_exc()
        return None


def generate_text(prompt: str, temperature: float = 0.1) -> str:
    """Генерация текстового ответа"""
    if not client:
        return prompt

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[prompt],
            config={"temperature": temperature}
        )
        return response.text.strip()
    except Exception as e:
        print(f"Ошибка генерации текста: {e}")
        return prompt


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Получение эмбеддингов для текстов"""
    if not client:
        return []

    try:
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
        return [emb.values for emb in response.embeddings]
    except Exception as e:
        print(f"Ошибка эмбеддинга: {e}")
        traceback.print_exc()
        return []
