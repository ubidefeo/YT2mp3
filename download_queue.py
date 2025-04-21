from telegram import Update
from telegram.ext import ContextTypes
import asyncio
import yaml
import time 
import os
import yt_dlp

save_path = None
executor = None
admins = []
users = []
is_downloading = False
TG_TOKEN = None
current_download_process = None
should_stop_download = False

def queue_init(config):
    global save_path, executor, admins, users, TG_TOKEN
    global current_download_process, should_stop_download

    save_path = config['save_path']
    executor = config['executor']
    admins = config['admins']
    users = config['users']
    TG_TOKEN = config['token']
    should_stop_download = config.get('should_stop_download', False)
    current_download_process = config.get('current_download_process', None)

def load_queue():
    try:
        with open('queue.yml', 'r') as file:
            data = yaml.safe_load(file)
            
        if data is None or 'queue' not in data:
            data = {
                'active': False,
                'current': None,
                'queue': [],
                'history': [],
                'settings': {
                    'max_queue_size': 10,
                    'max_history_size': 20
                }
            }
            save_queue(data)
        return data
    except FileNotFoundError:
        default_queue = {
            'active': False,
            'current': None,
            'queue': [],
            'history': [],
            'settings': {
                'max_queue_size': 10,
                'max_history_size': 20
            }
        }
        save_queue(default_queue)
        return default_queue

def save_queue(queue_data):
    import copy
    import json
    queue_json = json.dumps(queue_data)
    queue_copy = json.loads(queue_json)
    with open('queue.yml', 'w') as file:
        yaml.dump(queue_copy, file, default_flow_style=False)

async def add_to_queue(url, user_id, update, notify = True):
    queue_data = load_queue()
    if len(queue_data['queue']) >= queue_data['settings']['max_queue_size']:
        await update.message.reply_text('Sorry, the download queue is full. Please try again later.')
        return False
    user_name = update.effective_user.first_name
    username = update.effective_user.username
    if username:
        user_mention = f"@{username}"
    else:
        user_mention = user_name
    queue_item = {
        'url': url,
        'requested_by': user_id,
        'user_mention': user_mention,
        'timestamp': int(time.time())
    }
    queue_data['queue'].append(queue_item)
    save_queue(queue_data)
    if notify:
        position = len(queue_data['queue'])
        await update.message.reply_text(f'Your download has been added to the queue at position {position} of {position}.')
    if not queue_data['active']:
        asyncio.create_task(process_queue())
    return True

async def purge_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text('Sorry, only admins can purge the queue and history.')
        return
    purge_type = "all"
    if context.args:
        arg = context.args[0].lower()
        if arg in ["queue", "history", "all"]:
            purge_type = arg
    queue_data = load_queue()
    if purge_type == "queue" or purge_type == "all":
        if is_downloading:
          current_item = queue_data['queue'][0]
        queue_data['queue'] = []
        queue_data['active'] = False
        queue_data['current'] = None
    if purge_type == "history" or purge_type == "all":
        queue_data['history'] = []
    if is_downloading:
      queue_data['queue'].append(current_item)
    save_queue(queue_data)
    if purge_type == "queue":
        await update.message.reply_text('✅ Download queue has been purged.')
    elif purge_type == "history":
        await update.message.reply_text('✅ Download history has been purged.')
    else:
        await update.message.reply_text('✅ Download queue and history have been purged.')

async def process_queue():
    global is_downloading
    while True:
        queue_data = load_queue()
        if not queue_data['queue'] or queue_data['active']:
            return
        queue_data['active'] = True
        queue_data['current'] = queue_data['queue'][0]
        next_item = queue_data['queue'][0]
        url = next_item['url']
        ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': True,
            }
        def get_video_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', 'Unknown Title')
        loop = asyncio.get_event_loop()
        current_title = await loop.run_in_executor(executor, get_video_info)
        queue_data['current']['title'] = current_title
        save_queue(queue_data)
        next_item['title'] = current_title
        user_id = next_item['requested_by']
        user_mention = next_item.get('user_mention', '')
        print(f"Processing queue item: {url} requested by {user_id}")
        from telegram import Bot
        bot = Bot(token=TG_TOKEN)
        try:
            await bot.send_message(chat_id=user_id, text=f'🔄 Starting download of: *{current_title}*', disable_web_page_preview=True, parse_mode='Markdown')
        except Exception as notification_error:
            print(f"Error sending notification: {notification_error}")
        is_downloading = True
        try:
            title, path = await download_from_queue(url, user_id)
            queue_data = load_queue()
            completed_item = queue_data['current']
            completed_item['completed_at'] = int(time.time())
            completed_item['title'] = title
            queue_data['history'].insert(0, completed_item)
            if len(queue_data['history']) > queue_data['settings']['max_history_size']:
                queue_data['history'] = queue_data['history'][:queue_data['settings']['max_history_size']]
            queue_data['queue'].pop(0)
            queue_data['active'] = False
            queue_data['current'] = None
            save_queue(queue_data)
            completion_message = f'✅ Download complete: {title}'
            if user_mention:
                completion_message += f'\nRequested by {user_mention}'
            await bot.send_message(chat_id=user_id, text=completion_message)
        except Exception as e:
            print(f"Error processing queue item: {e}")
            if "Download manually stopped" in str(e):
                expanded_path = os.path.expanduser(save_path)
                cleanup_temp_files()
                await bot.send_message(
                    chat_id=user_id,
                    text=f'❌ Download was manually stopped.',
                    disable_web_page_preview=True
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=f'❌ Error downloading: {str(e)}',
                    disable_web_page_preview=True
                )
            queue_data = load_queue()
            queue_data['active'] = False
            queue_data['current'] = None
            if len(queue_data['queue']) > 0:
                queue_data['queue'].pop(0)
            save_queue(queue_data)
        finally:
            is_downloading = False

async def recover_queue():
    """
    Check if there was an interrupted download and recover the queue.
    """
    queue_data = load_queue()
    if queue_data['active'] and queue_data['current']:
        print("Found interrupted download, recovering...")
        cleanup_temp_files()
        queue_data['active'] = False
        queue_data['queue'].insert(0, queue_data['current'])
        queue_data['current'] = None
        save_queue(queue_data)
        asyncio.create_task(process_queue())
        print("Queue recovered and processing restarted")

async def download_from_queue(url, user_id=None):
    global current_download_process, should_stop_download
    should_stop_download = False
    
    def download_task():
        global should_stop_download
        expanded_path = os.path.expanduser(save_path)
        destination_path = expanded_path + '/%(title)s.%(ext)s'
        
        ydl_opts = {
            'outtmpl': destination_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',
            }],
            'keepvideo': True,
            'progress_hooks': [lambda d: check_stop_flag(d)],
            'no_warnings': True
        }
        
        def check_stop_flag(d):
            if should_stop_download:
                raise Exception("Download manually stopped")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                track_title = info_dict['title']
                if should_stop_download:
                    raise Exception("Download manually stopped")
                track_info = ydl.extract_info(url, download=True)
                track_title = track_info['title']
                converted_path = expanded_path + '/' + track_title + '.mp3'
                if should_stop_download:
                    raise Exception("Download manually stopped")
                if os.path.exists(converted_path):
                    file_time = time.time()
                    os.utime(converted_path, (file_time, file_time))
                    for file in os.listdir(expanded_path):
                        file_path = os.path.join(expanded_path, file)
                        if (file.startswith(track_title) and 
                            not file.endswith('.mp3') and 
                            os.path.isfile(file_path)):
                            try:
                                os.remove(file_path)
                                print(f"Deleted original file: {file}")
                            except Exception as e:
                                print(f"Warning: Could not delete original file {file}: {e}")
                
                return track_title, converted_path
                
        except Exception as e:
            if "Download manually stopped" in str(e):
                raise Exception("Download manually stopped")
            raise
    loop = asyncio.get_event_loop()
    try:
        current_download_process = True
        return await loop.run_in_executor(executor, download_task)
    finally:
        current_download_process = None

async def handle_playlist(url, user_id, update):
    """Handle a YouTube playlist by temporarily expanding the queue size"""
    queue_data = load_queue()
    original_max_size = queue_data['settings']['max_queue_size']
    try:
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and len(info.get('entries', [])) > 1:
                playlist_title = info.get('title', 'Playlist')
                videos = info.get('entries', [])
                video_count = len(videos)
                await update.message.reply_text(f"Detected playlist: {playlist_title} with {video_count} videos.")
                queue_data = load_queue()
                queue_data['settings']['original_max_queue_size'] = queue_data['settings']['max_queue_size']
                queue_data['settings']['max_queue_size'] = max(original_max_size, video_count)
                save_queue(queue_data)
                videos_added = 0
                for entry in videos:
                    video_url = entry.get('url')
                    if video_url:
                        user_name = update.effective_user.first_name
                        username = update.effective_user.username
                        if username:
                            user_mention = f"@{username}"
                        else:
                            user_mention = user_name
                        queue_item = {
                            'url': video_url,
                            'requested_by': user_id,
                            'user_mention': user_mention,
                            'timestamp': int(time.time())
                        }
                        queue_data['queue'].append(queue_item)
                        videos_added += 1
                save_queue(queue_data)
                if not queue_data['active'] and videos_added > 0:
                    asyncio.create_task(process_queue())
                queue_data = load_queue()
                if queue_data['settings'].get('original_max_queue_size'):
                    queue_data['settings']['max_queue_size'] = queue_data['settings']['original_max_queue_size']
                    del queue_data['settings']['original_max_queue_size']
                save_queue(queue_data)
                await update.message.reply_text(f"Added {videos_added} videos from playlist to the queue.")
                return True
    except Exception as e:
        print(f"Error processing playlist: {e}")
    return False

async def stop_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins:
        await update.message.reply_text('Sorry, only admins can stop all downloads.')
        return
    queue_data = load_queue()
    if queue_data['settings'].get('original_max_queue_size'):
        queue_data['settings']['max_queue_size'] = queue_data['settings']['original_max_queue_size']
        del queue_data['settings']['original_max_queue_size']
    queue_data['active'] = False
    queue_data['current'] = None
    queue_data['queue'] = []
    save_queue(queue_data)
    if get_download_process() is not None:
        set_stop_flag(True)
        await update.message.reply_text('❌ Stopping all downloads. Please wait...')
        await asyncio.sleep(1)
        if get_download_process() is not None:
            set_download_process(None)
    await update.message.reply_text('✅ All downloads have been stopped and queue cleared.')

async def skip_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins and user_id not in users:
        await update.message.reply_text('Sorry, you are not authorized to use this command.')
        return
    queue_data = load_queue()
    current_title = queue_data['current']['title'] if queue_data['current'] else 'Unknown'
    if queue_data['active'] and get_download_process() is not None:
        set_stop_flag(True)
        await update.message.reply_text(f"⏭️ Skipping *{current_title}*.\nProcessing next item in queue...", parse_mode='Markdown')
    else:
        await update.message.reply_text('❌ No active downloads to skip.')

async def queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins and user_id not in users:
        await update.message.reply_text('Sorry, you are not authorized to use this command.')
        return
    queue_data = load_queue()
    queue_length = len(queue_data['queue'])
    if queue_data['active']:
        current = queue_data['current']
        current_url = current['url']
        current_title = current['title']
        message = f"🔄 Currently downloading: *{current_title}*\n"
    else:
        message = "🔄 No active downloads.\n"
    message += f"📋 Queue length: {queue_length}\n"
    if queue_length > 0:
        message += "\nPending downloads:\n"
        for i, item in enumerate(queue_data['queue']):
            message += f"{i+1}. {item['url']}\n"
    await update.message.reply_text(message, disable_web_page_preview=True, parse_mode='Markdown')


async def current_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in admins and user_id not in users:
        if update.message:
            await update.message.reply_text('*Sorry, you are not authorized to use this command.*', parse_mode='Markdown')
        return
    queue_data = load_queue()
    if (queue_data['active'] and queue_data['current'] and 
        'url' in queue_data['current'] and 'title' in queue_data['current']):
        current = queue_data['current']
        current_url = current['url']
        current_title = current['title']
        user_mention = current.get('user_mention', 'Unknown')
        message = f"🔄 Currently downloading:\n*{current_title}*\n\nRequested by: {user_mention}\n\n{current_url}"
        await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=False)
    else:
        await update.message.reply_text('No download information available at the moment. Please try again in a few seconds.')

def set_stop_flag(value):
    global should_stop_download
    should_stop_download = value

def get_stop_flag():
    return should_stop_download

def set_download_process(value):
    global current_download_process
    current_download_process = value

def get_download_process():
    return current_download_process

def cleanup_temp_files():
    """
    Clean up temporary download files.
    """
    expanded_path = os.path.expanduser(save_path)
    try:
        for file in os.listdir(expanded_path):
            file_path = os.path.join(expanded_path, file)
            is_ytdl = file.endswith('.ytdl')
            is_part = file.endswith('.part')
            is_mp4 = file.endswith('.mp4')
            is_temp = is_ytdl or is_part or is_mp4
            if is_temp and os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted temporary file: {file}")
                except Exception as cleanup_error:
                    print(f"Warning: Could not delete temporary file {file}: {cleanup_error}")
    except Exception as cleanup_error:
        print(f"Error while cleaning up temporary files: {cleanup_error}")