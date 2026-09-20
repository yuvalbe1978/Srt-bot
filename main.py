import os
import pysrt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from googletrans import Translator

TOKEN = os.environ.get("TELEGRAM_TOKEN")
translator = Translator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלום! שלח לי קובץ .srt ואני אתרגם אותו לעברית.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    
    if not document.file_name.lower().endswith('.srt'):
        await update.message.reply_text("אנא שלח קובץ בפורמט .srt בלבד.")
        return

    await update.message.reply_text("הקובץ התקבל! מתחיל בתרגום, מייד אשלח את הקובץ המעודכן...")

    file = await context.bot.get_file(document.file_id)
    input_path = f"input_{document.file_id}.srt"
    await file.download_to_drive(input_path)

    output_filename = f"translated_{document.file_name}"

    try:
        subs = pysrt.open(input_path, encoding='utf-8')
        
        for sub in subs:
            if sub.text.strip():
                translated = translator.translate(sub.text, dest='he')
                sub.text = translated.text

        subs.save(output_filename, encoding='utf-8')

        with open(output_filename, 'rb') as doc:
            await update.message.reply_document(document=doc, filename=output_filename)

    except Exception as e:
        await update.message.reply_text(f"תרחשה שגיאה בזמן התרגום: {str(e)}")

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_filename):
            os.remove(output_filename)

if __name__ == '__main__':
    if not TOKEN:
        print("Error: No TELEGRAM_TOKEN provided!")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Bot is running...")
    app.run_polling()
