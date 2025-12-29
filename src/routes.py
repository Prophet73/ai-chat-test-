# routes.py - Основные роуты приложения
import os
import uuid
import json
import traceback
from datetime import datetime
from typing import Generator

from flask import Blueprint, render_template, request, jsonify, session, send_from_directory, Response

from src.config import TEXT_INSTRUCTIONS_DIR, PDF_DATA_DIR
from src.auth import login_required, get_current_user
from src.prompts import (
    RAG_SYSTEM_PROMPT, GROUNDING_SYSTEM_PROMPT,
    PRESCRIPTION_SYSTEM_PROMPT, GENERAL_CHAT_SYSTEM_PROMPT
)
from src.gemini_client import stream_response
from src.rag import (
    get_user_intent, should_rerun_rag, route_query_to_docs,
    find_relevant_chunks, get_full_docx_text, build_tree_from_manifest
)

main_bp = Blueprint('main', __name__)

# Хранилище сессий
sessions = {}


def get_or_create_session(session_id: str) -> dict:
    """Получить или создать сессию"""
    if session_id not in sessions:
        sessions[session_id] = {
            'history': [],
            'state': 'IDLE',
            'data': {},
            'last_rag_context': None,
            'last_rag_sources': None
        }
    return sessions[session_id]


def process_user_request(user_input: str, doc_id: str, session_id: str, category_doc_ids: str = None) -> Generator:
    """Обработка запроса пользователя"""
    current_session = get_or_create_session(session_id)
    current_session['history'].append({"role": "user", "content": user_input})

    state = current_session.get('state', 'IDLE')
    intent, initial_description = get_user_intent(user_input)

    if state.startswith("PRESCRIPTION"):
        intent = "PRESCRIPTION_REQUEST"

    full_response = ""
    final_sources = []

    # Общий чат
    if intent == "GENERAL_CHAT":
        response_generator = stream_response(
            history=current_session['history'],
            system_prompt=GENERAL_CHAT_SYSTEM_PROMPT
        )

    # Предписание
    elif intent == "PRESCRIPTION_REQUEST":
        def run_prescription_logic():
            nonlocal current_session, state, initial_description

            if state == 'IDLE' and not initial_description:
                current_session['state'] = 'PRESCRIPTION_AWAITING_DETAILS'
                message = "Пожалуйста, уточните, по какому виду работ выявлено нарушение?"
                yield "message", message
                return

            if (state == 'IDLE' and initial_description) or state == 'PRESCRIPTION_AWAITING_DETAILS':
                work_description = initial_description or user_input
                current_session['data']['work_description'] = work_description

                doc_ids = route_query_to_docs(work_description)
                if not doc_ids:
                    yield "error", f"Не найдены документы для '{work_description}'."
                    current_session['state'] = 'IDLE'
                    return

                sources, context, error = find_relevant_chunks(doc_ids, work_description, top_k=5)
                if error:
                    yield "error", f"Нет информации о '{work_description}'."
                    current_session['state'] = 'IDLE'
                    return

                current_session['state'] = 'PRESCRIPTION_AWAITING_CONFIRMATION'
                current_session['data']['found_sources'] = sources

                prompt = f"КОНТЕКСТ:\n{context}\n\nЗАДАЧА: Сгенерируй список нарушений для '{work_description}' (ШАГ 2)."
                yield "generator", stream_response([{"role": "user", "content": prompt}], PRESCRIPTION_SYSTEM_PROMPT)
                return

            if state == 'PRESCRIPTION_AWAITING_CONFIRMATION':
                found_sources = current_session['data'].get('found_sources', [])
                sources_text = "\n".join([
                    f"- Пункт {c.get('section_header', '')} из '{c.get('doc_name', '')}': {c.get('text', '')}"
                    for c in found_sources
                ])

                prompt = (
                    f"ПОДТВЕРЖДЕННЫЕ НАРУШЕНИЯ: '{user_input}'\n\n"
                    f"ДАННЫЕ:\n{sources_text}\n\n"
                    f"ДАТА: {datetime.now().strftime('%d.%m.%Y')}\n\n"
                    f"ЗАДАЧА: Сформируй предписание (ШАГ 3)."
                )
                yield "generator", stream_response([{"role": "user", "content": prompt}], PRESCRIPTION_SYSTEM_PROMPT)
                current_session['state'] = 'IDLE'
                current_session['data'] = {}
                return

        logic_output = run_prescription_logic()
        result_type, result_value = next(logic_output, (None, None))

        if result_type == "message":
            full_response = result_value
            response_generator = (f"data: {json.dumps({'type': 'content', 'data': result_value})}\n\n" for _ in [0])
        elif result_type == "error":
            full_response = result_value
            response_generator = (f"data: {json.dumps({'type': 'error', 'data': result_value})}\n\n" for _ in [0])
        elif result_type == "generator":
            response_generator = result_value
        else:
            full_response = "Ошибка в логике предписаний."
            current_session['state'] = 'IDLE'
            response_generator = (f"data: {json.dumps({'type': 'error', 'data': full_response})}\n\n" for _ in [0])

    # RAG-запрос
    else:
        if doc_id != '0':
            full_text, error = get_full_docx_text(doc_id)
            if error:
                yield f"data: {json.dumps({'type': 'error', 'data': error})}\n\n"
                return

            history = [{"role": "user", "content": f"ДОКУМЕНТ:\n---\n{full_text}\n---\n\nВОПРОС: {user_input}"}]
            response_generator = stream_response(history, GROUNDING_SYSTEM_PROMPT)
        else:
            run_new_search = should_rerun_rag(current_session['history'])
            context_text = None

            if not run_new_search and current_session.get('last_rag_context'):
                context_text = current_session['last_rag_context']
                final_sources = current_session.get('last_rag_sources', [])
            else:
                if category_doc_ids:
                    doc_ids = category_doc_ids.split(',')
                else:
                    contextual_query = "\n".join([f"{m['role']}: {m['content']}" for m in current_session['history']])
                    doc_ids = route_query_to_docs(contextual_query)

                if not doc_ids:
                    yield f"data: {json.dumps({'type': 'error', 'data': 'Не определены документы.'})}\n\n"
                    return

                sources, context, error = find_relevant_chunks(doc_ids, user_input)
                if error:
                    yield f"data: {json.dumps({'type': 'error', 'data': f'Нет информации: {error}'})}\n\n"
                    return

                context_text = context
                final_sources = sources
                current_session['last_rag_context'] = context_text
                current_session['last_rag_sources'] = final_sources

            contextual_query = "\n".join([f"{m['role']}: {m['content']}" for m in current_session['history']])
            history_with_context = current_session['history'][:-1] + [{
                'role': 'user',
                'content': f"**КОНТЕКСТ:**\n{context_text}\n\n**ДИАЛОГ:**\n{contextual_query}\n\n**ВОПРОС:** {user_input}"
            }]
            response_generator = stream_response(history_with_context, RAG_SYSTEM_PROMPT)

    # Отправка ответа
    for chunk_data in response_generator:
        yield chunk_data
        if chunk_data.strip().startswith("data:"):
            try:
                data = json.loads(chunk_data.strip()[5:])
                if data.get('type') == 'content':
                    full_response += data.get('data', '')
            except json.JSONDecodeError:
                pass

    if final_sources:
        yield f"data: {json.dumps({'type': 'sources', 'data': final_sources})}\n\n"

    if full_response:
        current_session['history'].append({"role": "model", "content": full_response})

    if len(current_session['history']) > 20:
        current_session['history'] = current_session['history'][-10:]


def stream_with_context(generator):
    """Обёртка для стриминга"""
    from flask import current_app
    with current_app.app_context():
        yield from generator


# --- Роуты ---

@main_bp.route('/')
@login_required
def index():
    if 'session_id' not in session or session['session_id'] not in sessions:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        sessions[session_id] = {
            'history': [], 'state': 'IDLE', 'data': {},
            'last_rag_context': None, 'last_rag_sources': None
        }

    user = get_current_user()
    return render_template('index.html', session_id=session['session_id'], user=user)


@main_bp.route('/get_documents_tree', methods=['GET'])
@login_required
def get_documents_tree():
    return jsonify(build_tree_from_manifest())


@main_bp.route('/get_response', methods=['POST'])
@login_required
def get_response():
    try:
        data = request.get_json()
        user_input = data.get('user_input')
        doc_id = data.get('doc_id')
        session_id = data.get('session_id')
        category_doc_ids = data.get('category_doc_ids')

        if not all([user_input, doc_id is not None, session_id]):
            def error_stream():
                yield f"data: {json.dumps({'type': 'error', 'data': 'Отсутствуют параметры'})}\n\n"
            return Response(error_stream(), mimetype='text/event-stream')

        return Response(
            stream_with_context(process_user_request(user_input, doc_id, session_id, category_doc_ids)),
            mimetype='text/event-stream'
        )
    except Exception as e:
        traceback.print_exc()
        def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': f'Ошибка: {e}'})}\n\n"
        return Response(error_stream(), mimetype='text/event-stream')


@main_bp.route('/switch_session', methods=['POST'])
@login_required
def switch_session():
    old_session_id = (request.get_json() or {}).get('session_id') or session.get('session_id')

    if old_session_id and old_session_id in sessions:
        sessions.pop(old_session_id, None)

    new_session_id = str(uuid.uuid4())
    session['session_id'] = new_session_id
    sessions[new_session_id] = {
        'history': [], 'state': 'IDLE', 'data': {},
        'last_rag_context': None, 'last_rag_sources': None
    }

    return jsonify({'message': 'Контекст сброшен.', 'new_session_id': new_session_id})


@main_bp.route('/get_instruction_content', methods=['GET'])
@login_required
def get_instruction_content():
    return jsonify({
        'rag_prompt': RAG_SYSTEM_PROMPT,
        'grounding_prompt': GROUNDING_SYSTEM_PROMPT
    })


@main_bp.route('/get_pdf/<path:filename>')
@login_required
def get_document_file(filename):
    safe_filename = os.path.basename(os.path.normpath(filename))

    if ".." in safe_filename or safe_filename.startswith(("/", "\\")):
        return "Недопустимое имя файла.", 400

    doc_path = os.path.join(TEXT_INSTRUCTIONS_DIR, safe_filename)
    if os.path.exists(doc_path):
        return send_from_directory(TEXT_INSTRUCTIONS_DIR, safe_filename)

    pdf_path = os.path.join(PDF_DATA_DIR, safe_filename)
    if os.path.exists(pdf_path):
        return send_from_directory(PDF_DATA_DIR, safe_filename)

    return "Файл не найден.", 404
