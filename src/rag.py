# rag.py - RAG (Retrieval-Augmented Generation) логика
import os
import re
import json
import traceback
from typing import List, Tuple, Optional

import docx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.config import VECTOR_STORE_DIR, TEXT_INSTRUCTIONS_DIR, MANIFEST_PATH
from src.prompts import QUERY_EXPANSION_PROMPT
from src.gemini_client import (
    generate_json, generate_text, embed_texts,
    DocumentRouterResponse, RagDecision, client
)


# --- Загрузка манифеста документов ---
ALL_DOCUMENTS_METADATA = []

try:
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        ALL_DOCUMENTS_METADATA = json.load(f)
    print(f"INFO: Манифест документов загружен ({len(ALL_DOCUMENTS_METADATA)} шт.)")
except Exception as e:
    print(f"ОШИБКА: Не удалось загрузить манифест: {e}")


def get_document_metadata():
    """Получить метаданные всех документов"""
    return ALL_DOCUMENTS_METADATA


def get_full_docx_text(doc_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Получить полный текст документа DOCX"""
    doc_info = next((doc for doc in ALL_DOCUMENTS_METADATA if doc['id'] == doc_id), None)
    if not doc_info or 'filename' not in doc_info:
        return None, "Информация о файле не найдена в манифесте."

    filepath = os.path.join(TEXT_INSTRUCTIONS_DIR, doc_info['filename'])
    if not os.path.exists(filepath):
        return None, f"Файл {doc_info['filename']} не найден."

    try:
        document = docx.Document(filepath)
        full_text = '\n'.join([p.text for p in document.paragraphs])

        start_marker = "<<ТЕКСТ НОРМАТИВА НАЧАЛО>>"
        marker_pos = full_text.find(start_marker)
        if marker_pos != -1:
            full_text = full_text[marker_pos + len(start_marker):]

        return full_text.strip(), None
    except Exception as e:
        traceback.print_exc()
        return None, f"Ошибка чтения файла: {e}"


def get_user_intent(user_query: str) -> Tuple[str, Optional[str]]:
    """Определить намерение пользователя"""
    query_lower = user_query.lower().strip()

    general_triggers = ['привет', 'hello', 'hi', 'здравствуй', 'добрый день', 'спасибо', 'благодарю', 'thanks']
    if query_lower in general_triggers:
        return "GENERAL_CHAT", None

    prescription_triggers = ['предписание', 'prescript', 'выдать предписание', 'написать предписание', 'составь предписание']
    for trigger in prescription_triggers:
        if trigger in query_lower:
            description = user_query[user_query.lower().find(trigger) + len(trigger):].strip()
            for prep in ['по', 'за', 'на', 'о', 'об']:
                if description.lower().startswith(prep + ' '):
                    description = description[len(prep)+1:].strip()
            return "PRESCRIPTION_REQUEST", description if description else None

    return "RAG_QUERY", None


def should_rerun_rag(history: List[dict]) -> bool:
    """Определить, нужен ли новый RAG-поиск"""
    if not client or len(history) < 2:
        return True

    last_user_query = history[-1]['content']
    previous_model_response = history[-2]['content']

    prompt = f"""You are analyzing a conversation. Decide if a new search is required.

    Previous AI Response:
    ---
    {previous_model_response[:1500]}
    ---

    User's New Query: "{last_user_query}"

    - New topic = new search needed.
    - Follow-up ("tell me more") = no new search.

    Do we need a new search?
    """

    decision = generate_json(prompt, RagDecision)
    if decision:
        print(f"INFO: RAG-детектор: {'НОВЫЙ ПОИСК' if decision.requires_new_search else 'КЕШ'}. {decision.reason}")
        return decision.requires_new_search

    return True


def route_query_to_docs(user_query: str) -> List[str]:
    """Выбрать релевантные документы"""
    if not client or not ALL_DOCUMENTS_METADATA:
        return []

    docs_description = "\n".join([
        f"- ID: {d['id']}, Название: {d['name']}, Описание: {d['description']}"
        for d in ALL_DOCUMENTS_METADATA if d.get('id')
    ])

    prompt = (
        f"Select the most relevant documents for the user query. "
        f"Return JSON with ALL relevant document IDs.\n\n"
        f"AVAILABLE DOCUMENTS:\n{docs_description}\n\n"
        f"USER QUERY: \"{user_query}\""
    )

    response = generate_json(prompt, DocumentRouterResponse)
    if response:
        doc_ids = [doc.doc_id for doc in response.relevant_documents]
        print(f"INFO: Роутер выбрал: {doc_ids}")
        return doc_ids

    return []


def expand_query(user_query: str) -> str:
    """Расширить запрос ключевыми терминами"""
    prompt = QUERY_EXPANSION_PROMPT.format(query=user_query)
    expanded = generate_text(prompt, temperature=0.1)
    if expanded and expanded != user_query:
        print(f"INFO: Запрос расширен: '{user_query}' -> '{expanded}'")
    return expanded


def find_relevant_chunks(
    doc_ids: List[str],
    user_query: str,
    top_k: int = 8,
    similarity_threshold: float = 0.4
) -> Tuple[Optional[List[dict]], Optional[str], Optional[str]]:
    """Найти релевантные фрагменты"""
    if not client:
        return None, None, "Gemini не инициализирован."

    expanded_query = expand_query(user_query)
    queries = [user_query]
    if expanded_query != user_query:
        queries.append(expanded_query)

    embeddings = embed_texts(queries)
    if not embeddings:
        return None, None, "Ошибка получения эмбеддингов."

    original_emb = embeddings[0]
    expanded_emb = embeddings[1] if len(embeddings) > 1 else None

    all_chunks = []
    all_metadata = {}

    for doc_id in doc_ids:
        vector_file = os.path.join(VECTOR_STORE_DIR, f"{doc_id}_vectors.json")
        meta_file = os.path.join(VECTOR_STORE_DIR, f"{doc_id}_metadata.json")

        if not os.path.exists(vector_file) or not os.path.exists(meta_file):
            continue

        try:
            with open(vector_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            all_chunks.extend(chunks)
            all_metadata[doc_id] = metadata
        except Exception as e:
            print(f"Ошибка загрузки {doc_id}: {e}")

    if not all_chunks:
        return None, None, "Не найдено релевантных фрагментов."

    # Поиск по TOC
    toc_embs = []
    for doc_id, meta in all_metadata.items():
        for i, sec in enumerate(meta.get('table_of_contents', [])):
            if 'embedding' in sec:
                toc_embs.append((doc_id, i, sec['embedding']))

    if toc_embs:
        toc_matrix = np.array([emb for _, _, emb in toc_embs])
        similarities = cosine_similarity([original_emb], toc_matrix)[0]

        if expanded_emb is not None:
            exp_sim = cosine_similarity([expanded_emb], toc_matrix)[0]
            similarities = (similarities + exp_sim) / 2

        top_indices = np.argsort(similarities)[-top_k // 2:][::-1]

        grouped_context = []
        relevant_sources = []

        for idx in top_indices:
            if similarities[idx] < similarity_threshold:
                continue

            doc_id, toc_i, _ = toc_embs[idx]
            sec = all_metadata[doc_id]['table_of_contents'][toc_i]
            start, num = sec['start_chunk_index'], sec['num_chunks']
            sec_chunks = all_chunks[start:start+num]
            sec_text = '\n'.join(c['text'] for c in sec_chunks)

            grouped_context.append(f"Раздел '{sec['full_path']}':\n{sec_text}")
            relevant_sources.append({
                "header": sec['full_path'],
                "text": sec_text[:200] + "...",
                "doc_name": all_metadata[doc_id]['doc_name'],
                "similarity": float(similarities[idx])
            })

        context_text = "\n\n---\n\n".join(grouped_context)

    else:
        # Fallback: плоский поиск
        doc_embeddings = np.array([item['vector'] for item in all_chunks])
        similarities = cosine_similarity([original_emb], doc_embeddings)[0]

        if expanded_emb is not None:
            exp_sim = cosine_similarity([expanded_emb], doc_embeddings)[0]
            similarities = (similarities + exp_sim) / 2

        unique_chunks = {}
        for i, sim in enumerate(similarities):
            if sim >= similarity_threshold and len(all_chunks[i].get('text', '')) > 50:
                chunk_id = all_chunks[i]['chunk_id']
                if chunk_id not in unique_chunks or sim > unique_chunks[chunk_id]['similarity']:
                    chunk = all_chunks[i].copy()
                    chunk['similarity'] = float(sim)
                    unique_chunks[chunk_id] = chunk

        sorted_chunks = sorted(unique_chunks.values(), key=lambda x: x['similarity'], reverse=True)[:top_k]

        # Подтягиваем split-чанки
        base_to_chunks = {}
        for c in all_chunks:
            header = c['section_header']
            base_header = re.sub(r' \((часть \d+)\)$', '', header)
            if base_header not in base_to_chunks:
                base_to_chunks[base_header] = []
            base_to_chunks[base_header].append(c)

        expanded_chunks = []
        seen_ids = set()
        for chunk in sorted_chunks:
            base_header = re.sub(r' \((часть \d+)\)$', '', chunk['section_header'])
            if base_header in base_to_chunks:
                for related in base_to_chunks[base_header]:
                    if related['chunk_id'] not in seen_ids:
                        related_copy = related.copy()
                        related_copy['similarity'] = chunk['similarity']
                        expanded_chunks.append(related_copy)
                        seen_ids.add(related['chunk_id'])

        expanded_chunks.sort(key=lambda x: (-x['similarity'], x['section_header']))

        relevant_sources = [{
            "header": c.get('section_header', 'Н/Д'),
            "text": c.get('text', ''),
            "doc_name": c.get('doc_name', 'Н/Д'),
            "similarity": c['similarity']
        } for c in expanded_chunks]

        context_texts = [
            f"Из документа '{c.get('doc_name', '')}', раздел '{c.get('section_header', '')}':\n{c.get('text', '')}"
            for c in expanded_chunks
        ]
        context_text = "\n\n---\n\n".join(context_texts)

    return relevant_sources, context_text, None


def build_tree_from_manifest() -> List[dict]:
    """Построить дерево документов для UI"""
    categories = {}
    category_icons = {
        "Основные кодексы и законы": "fas fa-landmark",
        "Организация и общие работы": "fas fa-project-diagram",
        "Отделочные и изоляционные работы": "fas fa-paint-roller",
        "Специальные работы и защита": "fas fa-shield-alt",
        "Инженерные системы": "fas fa-cogs",
        "Корпоративные стандарты": "fas fa-building",
        "Другое": "fas fa-folder"
    }

    for doc in ALL_DOCUMENTS_METADATA:
        if doc['id'] == "0":
            continue

        cat_name = doc.get("category", "Другое")
        if cat_name not in categories:
            categories[cat_name] = {
                "name": cat_name,
                "icon": category_icons.get(cat_name, "fas fa-folder"),
                "children": []
            }

        categories[cat_name]["children"].append({
            "name": doc["name"],
            "doc_id_text": doc["id"],
            "filename": doc.get("filename"),
            "icon": "far fa-file-alt"
        })

    return list(categories.values())
