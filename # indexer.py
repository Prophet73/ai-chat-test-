import os
import mammoth
import time

# --- НАСТРОЙКИ ---
# Папка, где лежат исходные DOCX и PDF файлы
# Путь указан относительно корня проекта
SOURCE_DOCS_DIR = os.path.join("static", "data")

# Папка, куда будут сохраняться сконвертированные Markdown файлы
# Будет создана в корне проекта
MARKDOWN_OUTPUT_DIR = "Markdown_Docs"

def convert_docx_to_markdown(docx_path, md_path):
    """
    Конвертирует один DOCX файл в Markdown с помощью библиотеки mammoth.
    """
    print(f"⚙️  Конвертация файла: {os.path.basename(docx_path)}...")
    try:
        with open(docx_path, "rb") as docx_file:
            result = mammoth.convert_to_markdown(docx_file)
            markdown_content = result.value

        with open(md_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)
        
        print(f"✅  Успешно сохранено в: {md_path}")
        return True
    except Exception as e:
        print(f"❌  ОШИБКА при конвертации файла {os.path.basename(docx_path)}: {e}")
        return False

def main():
    """
    Главная функция для запуска процесса конвертации.
    """
    print("--- Запуск конвертера DOCX в Markdown ---")
    
    # Проверяем, существует ли папка с исходными файлами
    if not os.path.isdir(SOURCE_DOCS_DIR):
        print(f"❌ ОШИБКА: Папка с исходными документами '{SOURCE_DOCS_DIR}' не найдена.")
        return

    # Создаем папку для результатов, если ее нет
    os.makedirs(MARKDOWN_OUTPUT_DIR, exist_ok=True)
    
    # Получаем список ТОЛЬКО .docx файлов в исходной папке
    docx_files = [f for f in os.listdir(SOURCE_DOCS_DIR) if f.lower().endswith(".docx")]

    if not docx_files:
        print(f"⚠️  В папке '{SOURCE_DOCS_DIR}' не найдено ни одного .docx файла.")
        return
        
    print(f"Найдено .docx документов для конвертации: {len(docx_files)}\n")
    
    start_time = time.time()
    converted_count = 0
    
    for filename in docx_files:
        docx_filepath = os.path.join(SOURCE_DOCS_DIR, filename)
        # Имя md-файла будет таким же, но с другим расширением
        md_filename = os.path.splitext(filename)[0] + ".md"
        md_filepath = os.path.join(MARKDOWN_OUTPUT_DIR, md_filename)
        
        if convert_docx_to_markdown(docx_filepath, md_filepath):
            converted_count += 1
        print("-" * 20)

    end_time = time.time()
    total_time = end_time - start_time
    
    print("--- Конвертация завершена! ---")
    print(f"✓ Успешно обработано: {converted_count} из {len(docx_files)}")
    print(f"⏱️  Затраченное время: {total_time:.2f} сек.")

if __name__ == "__main__":
    main()