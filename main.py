import os
import time
import pysrt
from deep_translator import GoogleTranslator
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = os.getenv("TELEGRAM_TOKEN")

def start(update, context):
    update.message.reply_text("שלום! שלח לי קובץ .srt ואתרגם אותו לעברית.")

def handle_document(update, context):
    document = update.message.document
    if not document.file_name.endswith('.srt'):
        update.message.reply_text("אנא שלח קובץ בסיומת .srt בלבד.")
        return

    update.message.reply_text("מקבל את הקובץ ומתחיל בתרגום לעברית... נא להמתין.")
    file = context.bot.get_file(document.file_id)
    input_path = f"input_{document.file_id}.srt"
    output_filename = f"translated_{document.file_name}"
    file.download(input_path)

    start_time = time.time()

    try:
        # פתיחת הקובץ עם תמיכה בקידוד שונה
        try:
            subs = pysrt.open(input_path, encoding='utf-8')
        except Exception:
            subs = pysrt.open(input_path, encoding='latin-1')

        translator = GoogleTranslator(source='auto', target='he')

        # תרגום בקבוצות כדי למנוע חסימות מ-Google
        batch_size = 20
        for i in range(0, len(subs), batch_size):
            batch = subs[i:i + batch_size]
            for sub in batch:
                text = sub.text.strip()
                if text:
                    try:
                        translated_text = translator.translate(text)
                        if translated_text:
                            sub.text = translated_text
                    except Exception as err:
                        print(f"Error translating line: {err}")
            time.sleep(0.3)  # הפסקה קצרה למניעת חסימה

        subs.save(output_filename, encoding='utf-8')

        elapsed_time = int(time.time() - start_time)
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        time_str = f"{minutes} דקות ו-{seconds} שניות" if minutes > 0 else f"{seconds} שניות"

        with open(output_filename, 'rb') as doc:
            update.message.reply_document(
                document=doc, 
                caption=f"הנה הקובץ המתורגם לעברית!\n⏱️ זמן תרגום: {time_str}"
            )
    except Exception as e:
        update.message.reply_text(f"תרגום נכשל: {e}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_filename):
            os.remove(output_filename)

if __name__ == '__main__':
    if not TOKEN:
        print("Error: No TELEGRAM_TOKEN provided")
        exit(1)

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document, handle_document))
    updater.start_polling()
    updater.idle()
