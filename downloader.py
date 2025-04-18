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

from download_queue import queue_init, add_to_queue, process_queue, queue_status
import download_queue

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



async def download_from_queue(url, user_id=None):
    def download_task():
        # Expand the home directory if needed
        expanded_path = os.path.expanduser(save_path)
        
        destination_path = expanded_path + '/%(title)s.%(ext)s'
        ydl_opts = {
            'outtmpl': destination_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',
            }],
            'keepvideo': True,  # Keep the original video file to avoid deletion errors
        }
        
        track_title = None
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract the info to get the title
            info_dict = ydl.extract_info(url, download=False)
            track_title = info_dict['title']
            
            # Send encoding notification before downloading
            if user_id:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                from telegram import Bot
                bot = Bot(token=TG_TOKEN)
                loop.run_until_complete(bot.send_message(
                    chat_id=user_id,
                    text=f'⚙️ Starting encoding: {track_title}',
                    disable_web_page_preview=True
                ))
                loop.close()
            
            # Now download and process
            track_info = ydl.extract_info(url, download=True)
            track_title = track_info['title']  # Get the title again in case it changed
            
            converted_path = expanded_path + '/' + track_title + '.mp3'
            file_time = time.time()
            
            # Make sure the file exists before trying to modify its timestamp
            if os.path.exists(converted_path):
                os.utime(converted_path, (file_time, file_time))
                
                # Look for and delete any video files with the same base name
                # This handles files with format codes like .f616.mp4
                base_file_pattern = os.path.join(expanded_path, track_title)
                for file in os.listdir(expanded_path):
                    file_path = os.path.join(expanded_path, file)
                    # Check if this is a video file matching our base name
                    if file.startswith(track_title) and not file.endswith('.mp3') and os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            print(f"Deleted original file: {file}")
                        except Exception as e:
                            print(f"Warning: Could not delete original file {file}: {e}")
            
            return track_title, converted_path
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, download_task)


async def url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if user is authorized
    if user_id not in admins and user_id not in users:
        await update.message.reply_text('Sorry, you are not authorized to use this command.')
        return
    
    yt_url = " ".join(context.args)
    if not yt_url:
        await update.message.reply_text('Please provide a YouTube URL.')
        return
    
    # Add to queue instead of downloading directly
    await add_to_queue(yt_url, user_id, update)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username
    await update.message.reply_text(f'Your User ID: {user_id}\nYour Username: @{username}')


queue_init({
    'save_path': save_path,
    'executor': executor,
    'admins': admins,
    'users': users,
    'token': TG_TOKEN  # Add this
})


download_queue.download_from_queue = download_from_queue


app = ApplicationBuilder().token(TG_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("dl", url))
app.add_handler(CommandHandler("myid", get_id))
app.add_handler(CommandHandler("queue", queue_status))

app.run_polling()