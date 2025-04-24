#!/usr/bin/env python3
import sys
import os
import time
import yt_dlp


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
import concurrent.futures
import yaml
from . import download_queue


try:
  from .tg_token import TG_TOKEN
except ImportError:
  print('''
Rename the file tg_token_example.py to tg_token.py and make sure you gather
a Telegram bot token from @BotFather and place it in the file.
The token should be a string and look like this:
TG_TOKEN = '0123456789:Aa1Bb_Cc2Dd3Ee4Ff5Gg_-6Hh7Ii8JjKk9L'
''')
  sys.exit(1)

'''
Feel free to choose a different path for the downloaded files.
The script will not create this folder, so make sure it exists.
'''
save_path = '~/Downloads/yt-rips' 
is_downloading = False
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
current_download_process = None
should_stop_download = False

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command, including deep links for user approval."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    if context.args and user_id in admins:
        arg = context.args[0]
        if arg.startswith("grant_"):
            try:
                new_user_id = int(arg.split("_")[1])
                await grant_access(update, new_user_id)
                return
            except (ValueError, IndexError):
                await update.message.reply_text("Invalid approval link.")
                return
    welcome_message = (
        f"Hello {user_name}! Welcome to YT2mp3 Bot!\n\n"
        "I can help you download YouTube videos as MP3 files."
    )
    if user_id not in admins and user_id not in users:
        await update.message.reply_text(
            welcome_message + "\n\n⚠️ You need approval to use download features.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Request Access", callback_data="request_access")]
            ])
        )
    else:
        await update.message.reply_text(welcome_message)

async def request_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "request_access":
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        username = update.effective_user.username or "No username"
        if user_id in admins or user_id in users:
            await query.edit_message_text("You are already authorized to use this bot.")
            return
        await query.edit_message_text("Your access request has been sent to the admin. Please wait for approval.")
        bot_username = await context.bot.get_me()
        bot_username = bot_username.username
        approval_link = f"https://t.me/{bot_username}?start=grant_{user_id}"
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"Access request from:\n"
                        f"Name: {user_name}\n"
                        f"Username: @{username}\n"
                        f"ID: {user_id}\n\n"
                        f"Click the button below to approve this user."
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Approve User", url=approval_link)]
                    ])
                )
            except Exception as e:
                print(f"Error sending message to admin {admin_id}: {e}")

async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow users to request access to the bot."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    username = update.effective_user.username or "No username"
    if user_id in admins or user_id in users:
        await update.message.reply_text("You are already authorized to use this bot.")
        return
    await update.message.reply_text("Your access request has been sent to the admin. Please wait for approval.")
    bot_username = await context.bot.get_me()
    bot_username = bot_username.username
    approval_link = f"https://t.me/{bot_username}?start=grant_{user_id}"
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"Access request from:\n"
                    f"Name: {user_name}\n"
                    f"Username: @{username}\n"
                    f"ID: {user_id}\n\n"
                    f"Click the button below to approve this user."
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Approve User", url=approval_link)]
                ])
            )
        except Exception as e:
            print(f"Error sending message to admin {admin_id}: {e}")

async def grant_access(update: Update, new_user_id: int) -> None:
    """Grant access to a user and update the authorized users file."""
    global users
    if new_user_id in users:
        await update.message.reply_text(f"User ID {new_user_id} is already authorized.")
        return
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(current_dir, 'authorised_users.yml')
        with open(config_file, 'r') as file:
            data = yaml.safe_load(file)
        if 'users' not in data:
            data['users'] = []
        data['users'].append(new_user_id)
        users = data['users']
        with open(config_file, 'w') as file:
            yaml.dump(data, file, default_flow_style=False)
        await update.message.reply_text(f"User ID {new_user_id} has been granted access.")
        try:
            await update.get_bot().send_message(
                chat_id=new_user_id,
                text="✅ Your access request has been approved! You can now use all bot features."
            )
        except Exception as e:
            await update.message.reply_text(f"Note: Could not notify the user: {e}")
            
    except Exception as e:
        await update.message.reply_text(f"Error updating authorized users: {e}")

async def url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins and user_id not in users:
        await update.message.reply_text('Sorry, you are not authorized to use this command.')
        return
    yt_url = " ".join(context.args)
    if not yt_url:
        await update.message.reply_text('Please provide a YouTube URL.')
        return
    is_playlist = await download_queue.handle_playlist(yt_url, user_id, update)
    if not is_playlist:
        await download_queue.add_to_queue(yt_url, user_id, update)

async def url_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins and user_id not in users:
        await update.message.reply_text('Sorry, you are not authorized to use this command.')
        return
    yt_url = 'https://www.youtube.com/playlist?list=PLXfw2d8gdlIax3QQHbl5uCB54YWe6qyIN'
    is_playlist = await download_queue.handle_playlist(yt_url, user_id, update)
    if not is_playlist:
        await download_queue.add_to_queue(yt_url, user_id, update)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username
    await update.message.reply_text(f'Your User ID: {user_id}\nYour Username: @{username}')

async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands_text = """
*/help* - Show this help message
*/start* - Start the bot and get a welcome message (happens when you first press the "start" button)
*/get_access* - Format a message for the administrator to approve your access
*/hello* - Greet the bot
*/myid* - Get your user ID (send to admin to be allowed to download)
*/dl <url>* - Download a YouTube video (or playlist)
*/skip* - Skip the current download and continue to the next
*/stop* - Stop the current download
*/current* - Show the currently downloading item (with preview)
*/queue* - Check the download queue status
*/purge* - Clear the download queue (admins only)
*/test* - Test the bot with a sample URL (admins only)"""
    await update.message.reply_text(commands_text, parse_mode='Markdown')

def main():
    global admins, users
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_dir, 'authorised_users.yml')

    try:
        with open(config_file, 'r') as file:
          data = yaml.safe_load(file)
          admins = data['admins']
          users = data['users']
          print('Admins:', admins)
          print('Users:', users)
    except FileNotFoundError:
      print("YAML file not found. Rename 'authorised_users_example.yml' and fill the required data.")
      sys.exit(1)

    app = ApplicationBuilder().token(TG_TOKEN).build()
    
    download_queue.queue_init({
        'save_path': save_path,
        'executor': executor,
        'admins': admins,
        'users': users,
        'token': TG_TOKEN,
        'should_stop_download': should_stop_download,
        'current_download_process': current_download_process
    })

    app.add_handler(CallbackQueryHandler(request_button_callback))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("request", request_access))
    app.add_handler(CommandHandler("grant_access", grant_access))
    app.add_handler(CommandHandler("help", commands))
    app.add_handler(CommandHandler("myid", get_id))
    app.add_handler(CommandHandler("dl", url))
    app.add_handler(CommandHandler("queue", download_queue.queue_status))
    app.add_handler(CommandHandler("current", download_queue.current_download))
    app.add_handler(CommandHandler("purge", download_queue.purge_queue))
    app.add_handler(CommandHandler("stop", download_queue.stop_download))
    app.add_handler(CommandHandler("skip", download_queue.skip_download))
    app.add_handler(CommandHandler("test", url_test))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    app.job_queue.run_once(lambda _: download_queue.recover_queue(), 1)
    app.run_polling()

if __name__ == '__main__':
    main()