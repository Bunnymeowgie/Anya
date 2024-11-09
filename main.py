import os
import json
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from flask import Flask, request

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8014981050:AAFFPBSf9R3KEQf8fwFF4I0SWidxaxwodFI"  # Replace with your bot token

# Initialize bot instance
bot = Bot(token=BOT_TOKEN)

# Folder path for the Math PDFs
PDF_FOLDER_PATH = 'Math'

# Dictionary to store user classes
user_classes = {}
USER_CLASSES_FILE = 'user_classes.json'

# Load user classes from file
def load_user_classes():
    if os.path.exists(USER_CLASSES_FILE):
        with open(USER_CLASSES_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save user classes to file
def save_user_classes():
    with open(USER_CLASSES_FILE, 'w') as file:
        json.dump(user_classes, file)

# Initialize user classes from saved data
user_classes = load_user_classes()

# Group Chat ID for class selection
GROUP_CHAT_ID = -1002416009587  # Replace with your group's chat ID

# Function to handle the /start command for testing
async def start(update: Update, context):
    await update.message.reply_text("Hey😙 Thanks for checking me. Use /select_class in the group to choose your class and if you already did that then use /get <year>.")
    logger.info("Responded to /start command")

# Function to check chat ID
async def check_chat_id(update: Update, context):
    await update.message.reply_text(f"The chat ID for this group is: {update.message.chat.id}")

# Function to handle new users joining the group
async def new_member(update: Update, context):
    if update.message.chat.id != int(GROUP_CHAT_ID):
        return  # Ignore if not in specified group

    new_member = update.message.new_chat_members[0]
    user_id = new_member.id
    user_name = new_member.first_name  # Get the first name of the new member
    if user_id in user_classes:
        assigned_class = user_classes[user_id]
        await context.bot.send_message(chat_id=user_id, text=f"Uff 😩 You are already in Class {assigned_class}.")
        logger.info(f"User {user_id} attempted to select class but was already in Class {assigned_class}")
    else:
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f'class_{i}') for i in range(4, 13)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Welcome {user_name}! Please select your class:", reply_markup=reply_markup)

# Command to manually select class in group
async def select_class(update: Update, context):
    if update.message.chat.id != int(GROUP_CHAT_ID):
        await update.message.reply_text("Class selection is only available in our group 😆.")
        return

    user_id = update.message.from_user.id
    if user_id in user_classes:
        assigned_class = user_classes[user_id]
        await update.message.reply_text(f"Aith idiot, You are already in Class {assigned_class}.")
        logger.info(f"User {user_id} attempted to re-select class but was already in Class {assigned_class}")
    else:
        keyboard = [[InlineKeyboardButton(str(i), callback_data=f'class_{i}') for i in range(4, 13)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please select your class:", reply_markup=reply_markup)
        logger.info(f"Prompted user {user_id} for class selection in group")

# Callback for class selection in the group
async def class_selection(update: Update, context):
    if update.callback_query.message.chat.id != int(GROUP_CHAT_ID):
        return  # Ignore if not in specified group

    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    selected_class = query.data.split('_')[1]

    if user_id in user_classes:
        assigned_class = user_classes[user_id]
        await query.edit_message_text(text=f"Ufff 😩 You are already in Class oye {assigned_class}.")
        logger.info(f"User {user_id} attempted to re-select class but was already in Class {assigned_class}")
    else:
        user_classes[user_id] = selected_class
        save_user_classes()  # Save the new selection
        await query.edit_message_text(text=f"Class {selected_class} assigned! Now, use /get <pdf_Year> in private to view a PDF.")
        logger.info(f"Assigned class {selected_class} to user {user_id}")

# Handle the /get command in private chat, send PDF as document
async def get_pdf(update: Update, context):
    user_id = update.message.from_user.id
    if update.message.chat.type != 'private':
        await update.message.reply_text("Lol kid😆, send this command personally to me😏 to view PDF files.")
        return

    if user_id not in user_classes:
        await update.message.reply_text("Please use /select_class in the group to choose your class first.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Please provide the PDF Year.")
        return
    
    pdf_name = " ".join(context.args)
    class_folder = f"Class {user_classes[user_id]}"
    pdf_path = os.path.join(PDF_FOLDER_PATH, class_folder, f"{pdf_name}.pdf")

    if os.path.exists(pdf_path):
        try:
            await context.bot.send_document(chat_id=user_id, document=open(pdf_path, 'rb'), caption=f"Viewing: {pdf_name}")
            logger.info(f"Sent PDF {pdf_name}.pdf to user {user_id}")
            
            # Schedule deletion of chat in an hour
            schedule_message_deletion(context, user_id)
        
        except Exception as e:
            logger.error(f"Failed to send PDF {pdf_name}: {e}")
            await update.message.reply_text("There was an error processing the PDF file.")
    else:
        logger.warning(f"{pdf_name}.pdf not found in Class {user_classes[user_id]} folder.")
        await update.message.reply_text(f"{pdf_name}.pdf not found in Class {user_classes[user_id]} folder.")

# Function to schedule message deletion
def schedule_message_deletion(context, user_id):
    def delete_chat():
        logger.info(f"Deleting chat with user {user_id}")
        context.bot.send_message(chat_id=user_id, text="This chat will now be deleted.")
        context.bot.delete_chat(user_id)

    # Scheduler to delete messages after 1 hour
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_chat, 'interval', seconds=3600)
    scheduler.start()

# Flask app to handle webhooks
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    application.update_queue.put(update)  # Use update_queue to process updates
    return 'OK'

# Main function to run the bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('get', get_pdf))
    application.add_handler(CommandHandler('select_class', select_class))
    application.add_handler(CommandHandler('check_chat_id', check_chat_id))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    application.add_handler(CallbackQueryHandler(class_selection, pattern='^class_'))

    logger.info("Starting bot...")

    # Start Flask app in a separate thread
    from threading import Thread
    thread = Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    thread.start()

    # Start bot polling
    application.run_polling()

if __name__ == '__main__':
    main()
