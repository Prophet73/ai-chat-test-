// static/js/scripts.js (Версия 3.0: Ребрендинг под Severin Hub)

// --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И СОСТОЯНИЕ ---
let sessionId;
let treeSearchDebounceTimer;
let originalDocumentHtml = "";
let searchMatchesInDocument = [];
let currentMatchIndexInDocument = -1;

// --- DOM ЭЛЕМЕНТЫ ---
let chatContentDiv, messagesDiv, userInput, modelInstructionsTextarea, loadingIndicator,
    instructionsModal, documentTreeContainer, currentPromptInfoSpan, sendButton,
    treeSearchInput, resetSearchButton, documentViewerModal, documentViewerTitle,
    textDocViewerToolbar, pdfViewerInfoBar, documentTextViewerBody, pdfViewerIframe,
    documentSearchInput, documentSearchStatus, docSearchPrevBtn, docSearchNextBtn,
    docSearchResetBtn;

// ==========================================================================
// 1. ИНИЦИАЛИЗАЦИЯ
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    try {
        sessionId = document.body.dataset.sessionId;
        initializeElements();
        bindEventListeners();
        fetchAndBuildTree();
        showWelcomeMessage();
        updateInstructionsDisplay();
        currentPromptInfoSpan.textContent = "Автоматический выбор документа";
    } catch (e) {
        console.error("Критическая ошибка при инициализации:", e);
        handleInitializationError(`Ошибка в JavaScript: ${e.message}`);
    }
});

function initializeElements() {
    chatContentDiv = document.getElementById("chat_content");
    messagesDiv = document.getElementById("messages");
    userInput = document.getElementById("user_input");
    modelInstructionsTextarea = document.getElementById("model_instructions");
    loadingIndicator = document.getElementById("loadingIndicator");
    instructionsModal = document.getElementById("instructionsModal");
    documentTreeContainer = document.getElementById("documentTree");
    currentPromptInfoSpan = document.getElementById("currentPromptInfo");
    sendButton = document.getElementById("sendButton");
    treeSearchInput = document.getElementById("treeSearchInput");
    resetSearchButton = document.getElementById('resetSearchButton');
    documentViewerModal = document.getElementById('documentViewerModal');
    documentViewerTitle = document.getElementById('documentViewerTitle');
    textDocViewerToolbar = document.getElementById('textDocViewerToolbar');
    pdfViewerInfoBar = document.getElementById('pdfViewerInfoBar');
    documentTextViewerBody = document.getElementById('documentTextViewerBody');
    pdfViewerIframe = document.getElementById('pdfViewerIframe');
    documentSearchInput = document.getElementById('documentSearchInput');
    documentSearchStatus = document.getElementById('documentSearchStatus');
    docSearchPrevBtn = document.getElementById('docSearchPrev');
    docSearchNextBtn = document.getElementById('docSearchNext');
    docSearchResetBtn = document.getElementById('docSearchReset');
}

function bindEventListeners() {
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    userInput.addEventListener('input', () => { userInput.style.height = 'auto'; userInput.style.height = `${Math.max(44, Math.min(userInput.scrollHeight, 160))}px`; });
    
    document.querySelector('.instructions-btn').addEventListener('click', openModal);
    document.querySelector('.reset-btn').addEventListener('click', resetContext);
    
    // Закрытие модальных окон
    document.querySelectorAll('.close-modal-btn').forEach(btn => {
        btn.addEventListener('click', () => { closeModal(); closeDocumentViewerModal(); });
    });
    instructionsModal.querySelector('.modal-footer button').addEventListener('click', closeModal);
    window.addEventListener('click', (event) => { 
        if (event.target === instructionsModal) closeModal(); 
        if (event.target === documentViewerModal) closeDocumentViewerModal(); 
    });
    document.addEventListener('keydown', (event) => { if (event.key === "Escape") { closeModal(); closeDocumentViewerModal(); } });
    
    // Поиск по дереву
    treeSearchInput.addEventListener('input', () => { clearTimeout(treeSearchDebounceTimer); treeSearchDebounceTimer = setTimeout(filterTree, 300); });
    resetSearchButton.addEventListener('click', () => { clearTimeout(treeSearchDebounceTimer); treeSearchInput.value = ""; filterTree(); });
    
    // Поиск в документе
    docSearchPrevBtn.addEventListener('click', () => performDocumentSearch(true, -1));
    docSearchNextBtn.addEventListener('click', () => performDocumentSearch(true, 1));
    docSearchResetBtn.addEventListener('click', () => { documentSearchInput.value = ""; performDocumentSearch(false); });
    documentSearchInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') {e.preventDefault(); performDocumentSearch(true, 1);} });
}

// ==========================================================================
// 2. УПРАВЛЕНИЕ ДЕРЕВОМ ДОКУМЕНТОВ
// ==========================================================================
function fetchAndBuildTree() {
    fetch('/get_documents_tree')
        .then(response => {
            if (!response.ok) throw new Error(`Ошибка сети: ${response.statusText}`);
            return response.json();
        })
        .then(treeData => {
            documentTreeContainer.innerHTML = '';
            const corporateCategoryIcon = "fas fa-building"; 
            const categoryIcons = {
                "Основные кодексы и законы": "fas fa-landmark",
                "Организация и общие работы": "fas fa-project-diagram",
                "Отделочные и изоляционные работы": "fas fa-paint-roller",
                "Специальные работы и защита": "fas fa-shield-alt",
                "Инженерные системы": "fas fa-cogs",
                "Корпоративные стандарты": corporateCategoryIcon,
                "Другое": "fas fa-folder"
            };
            buildTree(documentTreeContainer, treeData, true, categoryIcons);
        })
        .catch(error => {
            handleInitializationError('Не удалось загрузить базу знаний с сервера.');
            console.error("Ошибка загрузки дерева:", error);
        });
}

function buildTree(parentElement, items, isRoot = true, categoryIcons = {}) {
    const ul = document.createElement('ul');
    ul.className = isRoot ? 'tree-ul-root' : 'tree-ul-nested';
    
    const fragment = document.createDocumentFragment();

    items.forEach(item => {
        const li = document.createElement('li');
        const anchor = document.createElement('a');
        anchor.href = "#";
        anchor.className = 'tree-item';
        
        const hasChildren = item.children && item.children.length > 0;
        const isCategory = hasChildren && !item.doc_id_text;

        anchor.dataset.promptName = item.name;

        if (isCategory) {
            li.classList.add('has-children', 'tree-category');
            anchor.dataset.itemType = 'category';
            const icon = categoryIcons[item.name] || item.icon || 'fas fa-folder';
            anchor.innerHTML = `<i class="${icon} fa-fw"></i><span class="item-text">${htmlDecode(item.name)}</span><span class="tree-item-toggle"><i class="fas fa-chevron-right"></i></span>`;
            
            const childDocIds = item.children.map(child => child.doc_id_text).filter(Boolean);
            if (childDocIds.length > 0) {
                anchor.dataset.childDocIds = childDocIds.join(',');
            }
            
        } else {
            li.classList.add('tree-document');
            anchor.dataset.itemType = 'document';
            anchor.dataset.docIdText = item.doc_id_text || '0';
            anchor.dataset.docFile = item.filename || '';
            if (item.doc_id_text && item.doc_id_text !== '0') {
                 anchor.dataset.pdfFile = `${item.doc_id_text}.pdf`;
            } else {
                 anchor.dataset.pdfFile = '';
            }

            const hasViewableFile = anchor.dataset.docFile || anchor.dataset.pdfFile;
            const viewButtonClass = hasViewableFile ? '' : 'no-action';
            const viewButtonTitle = hasViewableFile ? `Открыть ${item.name}` : 'Файл для просмотра отсутствует';
            
            anchor.innerHTML = `<i class="${item.icon || 'far fa-file-alt'} fa-fw"></i><span class="item-text">${htmlDecode(item.name)}</span><button class="view-doc-btn ${viewButtonClass}" title="${viewButtonTitle}"><i class="far fa-eye"></i></button>`;
        }

        anchor.querySelector('.item-text').dataset.originalText = item.name;
        
        const viewBtn = anchor.querySelector('.view-doc-btn');
        if (viewBtn) {
            viewBtn.onclick = (ev) => {
                ev.stopPropagation();
                if (!viewBtn.classList.contains('no-action')) {
                    openDocumentFileViewer(item.name, anchor.dataset.docFile, anchor.dataset.pdfFile);
                }
            };
        }

        anchor.onclick = (e) => {
            e.preventDefault();
            const currentLi = anchor.parentElement;
            
            if (isCategory) {
                currentLi.classList.toggle('open');
                const subUl = currentLi.querySelector('ul');
                if (subUl) {
                    subUl.style.maxHeight = currentLi.classList.contains('open') ? subUl.scrollHeight + "px" : null;
                }
            }

            const isActive = anchor.classList.contains('active');
            
            document.querySelectorAll('.document-tree .tree-item.active, .document-tree .tree-item.active-parent').forEach(el => el.classList.remove('active', 'active-parent'));
            
            if (!isActive) {
                anchor.classList.add('active');
                let parentLiLoop = currentLi.parentElement.closest('li.tree-category');
                while (parentLiLoop) {
                    parentLiLoop.querySelector(':scope > .tree-item')?.classList.add('active-parent');
                    parentLiLoop = parentLiLoop.parentElement.closest('li.tree-category');
                }
                currentPromptInfoSpan.textContent = anchor.dataset.promptName;
            } else {
                currentPromptInfoSpan.textContent = "Автоматический выбор документа";
            }
        };

        li.appendChild(anchor);

        if (hasChildren) {
            li.appendChild(buildTree(li, item.children, false, categoryIcons));
        }
        fragment.appendChild(li);
    });

    ul.appendChild(fragment);
    if (isRoot) parentElement.appendChild(ul);
    return ul;
}

function filterTree() {
    const searchTerm = treeSearchInput.value.toLowerCase().trim();
    const allItems = Array.from(documentTreeContainer.querySelectorAll("li"));
    const regex = new RegExp(searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");

    allItems.forEach(li => {
        const anchor = li.querySelector(".tree-item");
        const itemTextSpan = anchor?.querySelector(".item-text");

        li.classList.remove("hidden-by-search");
        if (itemTextSpan && itemTextSpan.dataset.originalText) {
            itemTextSpan.innerHTML = itemTextSpan.dataset.originalText;
        }
        if (li.classList.contains("has-children")) {
            li.classList.remove("open");
            const subUl = li.querySelector("ul");
            if (subUl) subUl.style.maxHeight = null;
        }
    });

    resetSearchButton.style.display = searchTerm ? "inline-flex" : "none";
    if (!searchTerm) return;

    const visibleItems = new Set();
    allItems.forEach(li => {
        const itemTextSpan = li.querySelector(".item-text");
        const originalText = itemTextSpan?.dataset.originalText;
        if (originalText?.toLowerCase().includes(searchTerm)) {
            itemTextSpan.innerHTML = originalText.replace(regex, match => `<mark>${match}</mark>`);
            visibleItems.add(li);
            let parent = li.parentElement?.closest("li.has-children");
            while (parent) {
                visibleItems.add(parent);
                parent = parent.parentElement?.closest("li.has-children");
            }
        }
    });

    allItems.forEach(li => {
        if (!visibleItems.has(li)) {
            li.classList.add("hidden-by-search");
        } else if (li.classList.contains("has-children")) {
            li.classList.add("open");
            const subUl = li.querySelector("ul");
            if (subUl) subUl.style.maxHeight = subUl.scrollHeight + "px";
        }
    });
}

// ==========================================================================
// 3. ЛОГИКА ЧАТА
// ==========================================================================
function sendMessage() {
    const userMessageText = userInput.value.trim();
    if (!userMessageText || sendButton.disabled) {
        if (!sendButton.disabled) {
            userInput.classList.add('error-pulse');
            setTimeout(() => userInput.classList.remove('error-pulse'), 500);
        }
        return;
    }
    
    const activeTreeItem = document.querySelector('.document-tree .tree-item.active');
    
    let docIdToSend = '0';
    let categoryDocIdsToSend = null;

    if (activeTreeItem) {
        if (activeTreeItem.dataset.itemType === 'document') {
            docIdToSend = activeTreeItem.dataset.docIdText || '0';
        } else if (activeTreeItem.dataset.itemType === 'category' && activeTreeItem.dataset.childDocIds) {
            categoryDocIdsToSend = activeTreeItem.dataset.childDocIds;
        }
    }
    
    removeWelcomeMessage();
    appendMessage(userMessageText, "user");
    userInput.value = "";
    userInput.style.height = '44px';
    loadingIndicator.style.display = "flex";
    sendButton.disabled = true;
    chatContentDiv.scrollTop = chatContentDiv.scrollHeight;

    const assistantMsgElement = appendMessage("", "assistant");
    const bubble = assistantMsgElement.querySelector('.message-bubble');
    const contentWrapper = assistantMsgElement.querySelector('.message-content-wrapper');
    let fullResponseText = "";

    const requestBody = {
        user_input: userMessageText,
        doc_id: docIdToSend,
        session_id: sessionId
    };
    if (categoryDocIdsToSend) {
        requestBody.category_doc_ids = categoryDocIdsToSend;
    }

    fetch('/get_response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}`);
        if (!response.body) throw new Error("Ответ сервера не содержит тела.");
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        const readStream = () => {
            reader.read().then(({ done, value }) => {
                if (done) {
                    loadingIndicator.style.display = "none";
                    sendButton.disabled = false;
                    userInput.focus();
                    return;
                }
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n\n');
                lines.forEach(line => {
                    if (line.startsWith('data:')) {
                        const jsonData = line.substring(5).trim();
                        if (!jsonData) return;
                        try {
                            const parsedData = JSON.parse(jsonData);
                            if (parsedData.type === 'content') {
                                fullResponseText += parsedData.data;
                                bubble.innerHTML = marked.parse(fullResponseText);
                            } else if (parsedData.type === 'sources') {
                                appendSources(contentWrapper, parsedData.data);
                            } else if (parsedData.type === 'error') {
                                assistantMsgElement.classList.add('error-message');
                                bubble.textContent = parsedData.data;
                            }
                        } catch (e) {
                            console.error('Ошибка парсинга JSON из потока:', jsonData, e);
                        }
                    }
                });
                chatContentDiv.scrollTo({ top: chatContentDiv.scrollHeight, behavior: 'auto' });
                readStream();
            }).catch(err => {
                console.error("Ошибка при чтении потока:", err);
                bubble.textContent = `Произошла ошибка при чтении ответа от сервера: ${err.message}`;
                loadingIndicator.style.display = "none"; 
                sendButton.disabled = false; 
                userInput.focus();
            });
        };
        readStream();
    })
    .catch(err => {
        console.error("Критическая сетевая ошибка:", err);
        assistantMsgElement.classList.add('error-message');
        bubble.textContent = `Критическая сетевая ошибка: ${err.message}. Проверьте консоль разработчика (F12) для деталей.`;
        loadingIndicator.style.display = "none"; 
        sendButton.disabled = false; 
        userInput.focus();
    });
}


function appendMessage(message, sender, isError = false) {
    removeWelcomeMessage();
    const msgWrapper = document.createElement("div");
    msgWrapper.className = `message ${sender}-message ${isError ? 'error-message' : ''}`;
    
    const avatar = `<div class="message-avatar"><i class="fas ${sender === 'user' ? 'fa-user' : 'fa-robot'}"></i></div>`;
    
    const copyButton = sender === 'assistant' 
        ? `<button class="copy-message-btn" title="Копировать ответ"><i class="far fa-copy"></i></button>` 
        : '';

    const bubble = `<div class="message-bubble"><div class="markdown-content">${marked.parse(message)}</div></div>`;
    const contentWrapperHTML = `<div class="message-content-wrapper">${bubble}${copyButton}</div>`;

    msgWrapper.innerHTML = sender === 'user' ? contentWrapperHTML + avatar : avatar + contentWrapperHTML;
    
    messagesDiv.appendChild(msgWrapper);

    if (sender === 'assistant') {
        const copyBtn = msgWrapper.querySelector('.copy-message-btn');
        if (copyBtn) {
            copyBtn.onclick = () => {
                const textToCopy = msgWrapper.querySelector('.message-bubble').innerText;
                copyToClipboard(textToCopy, copyBtn);
            };
        }
    }

    chatContentDiv.scrollTo({ top: chatContentDiv.scrollHeight, behavior: 'smooth' });
    return msgWrapper;
}

function appendSources(contentWrapper, sources) {
    if (!Array.isArray(sources) || sources.length === 0) return;
    const sourcesContainer = document.createElement('details');
    sourcesContainer.className = 'sources-container';
    const summary = document.createElement('summary');
    summary.innerHTML = '<i class="fas fa-book-open"></i> Показать источники';
    sourcesContainer.appendChild(summary);

    const groupedSources = sources.reduce((acc, source) => {
        const docName = source.doc_name || 'Неизвестный документ';
        if (!acc[docName]) acc[docName] = [];
        acc[docName].push(source);
        return acc;
    }, {});

    for (const docName in groupedSources) {
        const docGroup = document.createElement('div');
        docGroup.className = 'source-doc-group';
        docGroup.innerHTML = `<h6 class="source-doc-header"><i class="far fa-file-alt"></i> ${docName}</h6>`;
        
        const sourcesList = document.createElement('ul');
        sourcesList.className = 'sources-list-grouped';
        
        groupedSources[docName].forEach(source => {
            const sourceItem = document.createElement('li');
            sourceItem.className = 'source-item';
            const similarity = (source.similarity * 100).toFixed(0);
            sourceItem.innerHTML = 
                `<div class="source-item-section" title="Релевантность: ${similarity}%">
                    <strong>Раздел:</strong> ${source.header || 'Общие положения'} 
                    <span class="source-similarity">(${similarity}%)</span>
                 </div>
                 <p class="source-item-text">${source.text}</p>`;
            sourcesList.appendChild(sourceItem);
        });
        docGroup.appendChild(sourcesList);
        sourcesContainer.appendChild(docGroup);
    }
    contentWrapper.appendChild(sourcesContainer);
}

function resetContext() {
    messagesDiv.innerHTML = "";
    showWelcomeMessage();
    fetch('/switch_session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) });
    document.querySelectorAll('.document-tree .tree-item.active, .document-tree .tree-item.active-parent').forEach(el => el.classList.remove('active', 'active-parent'));
    treeSearchInput.value = ""; filterTree();
    currentPromptInfoSpan.textContent = "Автоматический выбор документа";
    sendButton.disabled = false; loadingIndicator.style.display = "none";
}

// ==========================================================================
// 4. МОДАЛЬНЫЕ ОКНА И ПРОСМОТРЩИК ДОКУМЕНТОВ
// ==========================================================================
function openModal(){ instructionsModal.style.display = "block"; }
function closeModal(){ instructionsModal.style.display = "none"; }
function openDocumentViewerModal(){ documentViewerModal.style.display = "block"; }
function closeDocumentViewerModal() {
    documentViewerModal.style.display = "none";
    documentTextViewerBody.innerHTML = "";
    pdfViewerIframe.src = "about:blank";
    originalDocumentHtml = "";
    searchMatchesInDocument = [];
    currentMatchIndexInDocument = -1;
    documentSearchInput.value = "";
    documentSearchStatus.textContent = "";
}

async function openDocumentFileViewer(docNameForTitle, docxFile, pdfFile) {
    closeDocumentViewerModal();
    documentViewerTitle.textContent = `Документ: ${docNameForTitle}`;
    
    textDocViewerToolbar.style.display = 'none';
    pdfViewerInfoBar.style.display = 'none';
    documentTextViewerBody.style.display = 'none';
    pdfViewerIframe.style.display = 'none';
    
    openDocumentViewerModal();

    if (docxFile) {
        documentTextViewerBody.style.display = 'block';
        textDocViewerToolbar.style.display = 'flex';
        documentTextViewerBody.innerHTML = '<p>Загрузка и обработка документа .docx...</p>';
        try {
            const response = await fetch(`/get_pdf/${encodeURIComponent(docxFile)}`);
            if (!response.ok) throw new Error(`Ошибка загрузки файла: ${response.statusText}`);
            const arrayBuffer = await response.arrayBuffer();
            const result = await mammoth.convertToHtml({ arrayBuffer: arrayBuffer });
            originalDocumentHtml = result.value.replace(/\[\d+\]/g, "");
            documentTextViewerBody.innerHTML = originalDocumentHtml;
            performDocumentSearch(false);
        } catch (error) {
            documentTextViewerBody.innerHTML = `<p style="color:red">Ошибка обработки .docx: ${error.message}</p>`;
        }
    } 
    else if (pdfFile) {
        pdfViewerIframe.style.display = 'block';
        pdfViewerInfoBar.style.display = 'flex';
        pdfViewerIframe.src = `/get_pdf/${encodeURIComponent(pdfFile)}`;
    } 
    else {
        documentTextViewerBody.style.display = 'block';
        documentTextViewerBody.innerHTML = '<p>Для этого элемента не прикреплен файл для просмотра.</p>';
    }
}

function performDocumentSearch(isNavigating = false, direction = 0) {
    if (!originalDocumentHtml) return;
    documentTextViewerBody.innerHTML = originalDocumentHtml;
    const searchTerm = documentSearchInput.value.trim();

    if (!searchTerm) {
        documentSearchStatus.textContent = "";
        docSearchPrevBtn.disabled = true;
        docSearchNextBtn.disabled = true;
        return;
    }

    const regex = new RegExp(searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    highlightTextNodes(documentTextViewerBody, regex);

    searchMatchesInDocument = Array.from(documentTextViewerBody.querySelectorAll("mark.doc-search-highlight"));
    
    if (searchMatchesInDocument.length > 0) {
        if (isNavigating) {
            currentMatchIndexInDocument = (currentMatchIndexInDocument + direction + searchMatchesInDocument.length) % searchMatchesInDocument.length;
        } else {
            currentMatchIndexInDocument = 0;
        }
        updateSearchHighlight();
    } else {
        documentSearchStatus.textContent = "Ничего не найдено";
        docSearchPrevBtn.disabled = true;
        docSearchNextBtn.disabled = true;
    }
}

function highlightTextNodes(node, regex) {
    if (node.nodeType === 3) {
        const parent = node.parentNode;
        if (parent && ["MARK", "SCRIPT", "STYLE"].includes(parent.tagName.toUpperCase())) return;

        if (node.nodeValue.match(regex)) {
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;
            node.nodeValue.replace(regex, (match, offset) => {
                if (offset > lastIndex) {
                    fragment.appendChild(document.createTextNode(node.nodeValue.substring(lastIndex, offset)));
                }
                const mark = document.createElement("mark");
                mark.className = "doc-search-highlight";
                mark.textContent = match;
                fragment.appendChild(mark);
                lastIndex = offset + match.length;
            });
            if (lastIndex < node.nodeValue.length) {
                fragment.appendChild(document.createTextNode(node.nodeValue.substring(lastIndex)));
            }
            parent?.replaceChild(fragment, node);
        }
    } else if (node.nodeType === 1 && !["SCRIPT", "STYLE", "MARK"].includes(node.tagName.toUpperCase())) {
        Array.from(node.childNodes).forEach(child => highlightTextNodes(child, regex));
    }
}

function updateSearchHighlight() {
    searchMatchesInDocument.forEach(mark => mark.classList.remove("current-match"));
    const currentMatch = searchMatchesInDocument[currentMatchIndexInDocument];
    if (currentMatch) {
        currentMatch.classList.add("current-match");
        currentMatch.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    documentSearchStatus.textContent = `${currentMatchIndexInDocument + 1}/${searchMatchesInDocument.length}`;
    docSearchPrevBtn.disabled = false;
    docSearchNextBtn.disabled = false;
}

// ==========================================================================
// 5. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ==========================================================================
function htmlDecode(input) {
    const doc = new DOMParser().parseFromString(input, "text/html");
    return doc.documentElement.textContent;
}

function showWelcomeMessage() {
    if (messagesDiv.children.length > 0) return;
    messagesDiv.innerHTML = `<div class="welcome-message-container">
        <div class="welcome-icon"><i class="fas fa-atom"></i></div>
        <h3>Добро пожаловать в Severin Hub!</h3>
        <p>Я — ваш умный помощник по базе знаний и стандартам компании.</p>
        <strong>Мои основные функции:</strong>
        <ul>
            <li><strong>Консультация:</strong> Задайте любой вопрос по нормативам, корпоративным стандартам или процедурам.</li>
            <li><strong>Аудит:</strong> Опишите ситуацию, и я помогу определить, есть ли нарушения и какие пункты стандартов затронуты.</li>
            <li><strong>Документы:</strong> Помогу составить проект предписания или другого документа на основе найденных нарушений.</li>
        </ul>
        <p>Начните с вопроса в строке ниже или выберите раздел в базе знаний слева.</p>
    </div>`;
}

function removeWelcomeMessage() {
    const welcomeMsg = messagesDiv.querySelector(".welcome-message-container");
    if (welcomeMsg) welcomeMsg.remove();
}

function handleInitializationError(message) {
    documentTreeContainer.innerHTML = `<p style='color:red; padding:10px;'>${message}</p>`;
    currentPromptInfoSpan.textContent = "Ошибка инициализации";
}

function updateInstructionsDisplay() {
    fetch("/get_instruction_content")
        .then(res => res.json())
        .then(data => {
            if (data.rag_prompt && data.grounding_prompt) {
                modelInstructionsTextarea.value = `--- ИНСТРУКЦИЯ ДЛЯ РЕЖИМА ПОИСКА (RAG) ---\n${data.rag_prompt}\n\n\n--- ИНСТРУКЦИЯ ДЛЯ РЕЖИМА ЗАЗЕМЛЕНИЯ (GROUNDING) ---\n${data.grounding_prompt}`;
            } else {
                modelInstructionsTextarea.value = "Не удалось загрузить инструкции.";
            }
        })
        .catch(err => {
            console.error("Ошибка загрузки инструкций:", err);
            modelInstructionsTextarea.value = "Ошибка при загрузке инструкций с сервера.";
        });
}

function copyToClipboard(text, buttonElement) {
    navigator.clipboard.writeText(text).then(() => {
        const originalIcon = buttonElement.innerHTML;
        buttonElement.innerHTML = '<i class="fas fa-check"></i>';
        buttonElement.classList.add('copied');
        setTimeout(() => {
            buttonElement.innerHTML = originalIcon;
            buttonElement.classList.remove('copied');
        }, 1500);
    }).catch(err => {
        console.error('Не удалось скопировать текст: ', err);
    });
}