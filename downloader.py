#!/usr/bin/env python3
import sys
import os
import time
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import concurrent.futures
import yaml
import download_queue


try:
  from tg_token import TG_TOKEN
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

try:
  with open('authorised_users.yml', 'r') as file:
      data = yaml.safe_load(file)
except FileNotFoundError:
  print("YAML file not found. Rename 'authorised_users_example.yml' and fill the required data.")
  sys.exit(1)

admins = data['admins']
users = data['users']

print('Admins:', admins)
print('Users:', users)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

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
/hello - Greet the bot
/dl <url> - Download a YouTube video
/stop - Stop the current download
/skip - Skip the current download and continue to the next
/current - Show the currently downloading item (with preview)
/myid - Get your user ID (send to admin to be allowed to download)
/queue - Check the download queue status
/purge - Clear the download queue (admins only)
/help - Show this help message
/test - Test the bot with a sample URL (admins only)"""
    await update.message.reply_text(commands_text)

download_queue.queue_init({
    'save_path': save_path,
    'executor': executor,
    'admins': admins,
    'users': users,
    'token': TG_TOKEN,
    'should_stop_download': should_stop_download,
    'current_download_process': current_download_process
})

app = ApplicationBuilder().token(TG_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("help", commands))
app.add_handler(CommandHandler("myid", get_id))
app.add_handler(CommandHandler("dl", url))
app.add_handler(CommandHandler("queue", download_queue.queue_status))
app.add_handler(CommandHandler("current", download_queue.current_download))
app.add_handler(CommandHandler("purge", download_queue.purge_queue))
app.add_handler(CommandHandler("stop", download_queue.stop_download))
app.add_handler(CommandHandler("skip", download_queue.skip_download))
app.add_handler(CommandHandler("test", url_test))

app.job_queue.run_once(lambda _: download_queue.recover_queue(), 1)
app.run_polling()