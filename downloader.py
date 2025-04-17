#!/usr/bin/env python3
import sys
import os
import time
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import concurrent.futures
import asyncio
'''
Rename the file tg_token_example.py to tg_token.py and make sure you gather
a Telegram bot token from @BotFather and place it in the file.
The token should be a string and look like this:
TG_TOKEN = '0123456789:Aa1Bb_Cc2Dd3Ee4Ff5Gg_-6Hh7Ii8JjKk9L'
'''
from tg_token import TG_TOKEN
import yaml


# try:
#     video_url = sys.argv[1]
# except IndexError as e:
#     print(e)

'''
Feel free to choose a different path for the downloaded files.
The script will not create this folder, so make sure it exists.
'''
save_path = '~/Downloads/yt-rips' 

# Load the YAML file
with open('authorised_users.yml', 'r') as file:
    data = yaml.safe_load(file)

# Now you can access the data
admins = data['admins']
users = data['users']

print('Admins:', admins)
print('Users:', users)
is_downloading = False
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# async def download_best_audio_as_mp3(video_url, save_path=save_path, update=None):
#     global is_downloading
#     destination_path = save_path + '/%(title)s.%(ext)s'

#     ydl_opts = {
#         'outtmpl': destination_path,  # Save path and file name
#         'postprocessors': [{  # Post-process to convert to MP3
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',  # Convert to mp3
#             'preferredquality': '0',  # '0' means best quality, auto-determined by source
#         }],
#     }
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         track_info = ydl.extract_info(video_url, download=True)
#         track_title = track_info['title']
#         ydl_opts['outtmpl'] = save_path + '/' + track_info['title'] + '.%(ext)s'
#         converted_path = save_path + '/' + track_info['title'] + '.mp3'
#         # ydl.download([video_url])

#         print('>>>', converted_path)
    
#     file_time = time.time()
#     # print(destination_path)
#     # print(os.stat(destination_path))
#     os.utime(converted_path, (file_time, file_time))
#     await update.message.reply_text(f'I have successfully downloaded: {track_title}')
#     print('I have successfully downloaded:', track_title)
#     is_downloading = False

async def download_best_audio_as_mp3(video_url, save_path=save_path, update=None, context=None):
    global is_downloading
    is_downloading = True
    
    # Define the actual download function (synchronous)
    def download_task():
        destination_path = save_path + '/%(title)s.%(ext)s'
        ydl_opts = {
            'outtmpl': destination_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            track_info = ydl.extract_info(video_url, download=True)
            track_title = track_info['title']
            converted_path = save_path + '/' + track_title + '.mp3'
            file_time = time.time()
            os.utime(converted_path, (file_time, file_time))
            return track_title, converted_path
    
    try:
        # Run the download task in a separate thread
        loop = asyncio.get_event_loop()
        track_title, path = await loop.run_in_executor(executor, download_task)
        await update.message.reply_text(f'I have successfully downloaded: {track_title}')
        print('I have successfully downloaded:', track_title)
    except Exception as e:
        await update.message.reply_text(f'Error downloading: {str(e)}')
    finally:
        is_downloading = False


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global is_downloading
    yt_url = " ".join(context.args)
    if is_downloading:
        await update.message.reply_text('I am already downloading a file. Please wait.')
        return
    
    # Don't await the download function - schedule it and continue
    is_downloading = True
    await update.message.reply_text(f'I will download from {yt_url}', disable_web_page_preview=True)
    
    # Create a background task instead of awaiting
    asyncio.create_task(download_best_audio_as_mp3(yt_url, save_path, update, context))

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username
    await update.message.reply_text(f'Your User ID: {user_id}\nYour Username: @{username}')

app = ApplicationBuilder().token(TG_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("dl", url))
app.add_handler(CommandHandler("myid", get_id))

app.run_polling()