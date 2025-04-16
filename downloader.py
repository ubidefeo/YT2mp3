#!/usr/bin/env python3
import sys
import os
import time
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
'''
Rename the file tg_token_example.py to tg_token.py and make sure you gather
a Telegram bot token from @BotFather and place it in the file.
The token should be a string and look like this:
TG_TOKEN = '0123456789:Aa1Bb_Cc2Dd3Ee4Ff5Gg_-6Hh7Ii8JjKk9L'
'''
from tg_token import TG_TOKEN

try:
    video_url = sys.argv[1]
except IndexError as e:
    print(e)

'''
Feel free to choose a different path for the downloaded files.
The script will not create this folder, so make sure it exists.
'''
save_path = './Downloads/yt-rips' 

def download_best_audio_as_mp3(video_url, save_path=save_path):
    destination_path = save_path + '/%(title)s.%(ext)s'

    ydl_opts = {
        'outtmpl': destination_path,  # Save path and file name
        'postprocessors': [{  # Post-process to convert to MP3
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # Convert to mp3
            'preferredquality': '0',  # '0' means best quality, auto-determined by source
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        track_info = ydl.extract_info(video_url, download=True)
        ydl_opts['outtmpl'] = save_path + '/' + track_info['title'] + '.%(ext)s'
        converted_path = save_path + '/' + track_info['title'] + '.mp3'
        # ydl.download([video_url])

        print('>>>', converted_path)
    
    file_time = time.time()
    # print(destination_path)
    # print(os.stat(destination_path))
    os.utime(converted_path, (file_time, file_time))
# download_best_audio_as_mp3(video_url, save_path)

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

async def url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    yt_url = " ".join(context.args)
    await update.message.reply_text(f'I will download from {yt_url}')
    download_best_audio_as_mp3(yt_url, save_path)

app = ApplicationBuilder().token(TG_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("url", url))

app.run_polling()