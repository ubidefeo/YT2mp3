from telegram import Update
from telegram.ext import ContextTypes
import asyncio
import yaml
import time 
import os

# Queue management functions
save_path = None
executor = None
admins = []
users = []
is_downloading = False
TG_TOKEN = None

# Function to initialize the module
def queue_init(config):
    global save_path, executor, admins, users, TG_TOKEN
    save_path = config['save_path']
    executor = config['executor']
    admins = config['admins']
    users = config['users']
    TG_TOKEN = config['token']  # Add this

def load_queue():
    try:
        with open('queue.yml', 'r') as file:
            data = yaml.safe_load(file)
            
        # Check if the loaded data is None (empty file) or missing expected keys
        if data is None or 'queue' not in data:
            # Create default queue structure
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
        # Create default queue file if it doesn't exist
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
    with open('queue.yml', 'w') as file:
        yaml.dump(queue_data, file, default_flow_style=False)

async def add_to_queue(url, user_id, update):
    queue_data = load_queue()
    
    # Check if queue is at max capacity
    if len(queue_data['queue']) >= queue_data['settings']['max_queue_size']:
        await update.message.reply_text('Sorry, the download queue is full. Please try again later.')
        return False
    
    # Get user's name or username
    user_name = update.effective_user.first_name
    username = update.effective_user.username
    if username:
        user_mention = f"@{username}"
    else:
        user_mention = user_name
    
    # Add to queue
    queue_item = {
        'url': url,
        'requested_by': user_id,
        'user_mention': user_mention,
        'timestamp': int(time.time())
    }
    queue_data['queue'].append(queue_item)
    
    # Save queue
    save_queue(queue_data)
    
    # Notify user of position
    position = len(queue_data['queue'])
    await update.message.reply_text(f'Your download has been added to the queue at position {position} of {position}.')
    
    # Start queue processing if not active
    if not queue_data['active']:
        asyncio.create_task(process_queue())
    
    return True

async def process_queue():
    global is_downloading
    
    while True:
        queue_data = load_queue()
        
        # If queue is empty or already active, stop
        if not queue_data['queue'] or queue_data['active']:
            return
        
        # Mark queue as active
        queue_data['active'] = True
        queue_data['current'] = queue_data['queue'][0]
        save_queue(queue_data)
        
        # Get the next item
        next_item = queue_data['queue'][0]
        url = next_item['url']
        user_id = next_item['requested_by']
        user_mention = next_item.get('user_mention', '')  # Get user mention with fallback
        
        # Notify in console
        print(f"Processing queue item: {url} requested by {user_id}")
        
        # Send notification to the user that download is starting
        from telegram import Bot
        bot = Bot(token=TG_TOKEN)
        await bot.send_message(chat_id=user_id, text=f'🔄 Starting download of: {url}', disable_web_page_preview=True)
        
        # Process download
        is_downloading = True
        try:
            # You would need to modify download_best_audio_as_mp3 to work with queue items
            # or create a separate function for queue processing
            title, path = await download_from_queue(url, user_id)
            
            # Add to history
            queue_data = load_queue()  # Reload to get latest state
            completed_item = queue_data['current']
            completed_item['completed_at'] = int(time.time())
            completed_item['title'] = title
            
            queue_data['history'].insert(0, completed_item)
            if len(queue_data['history']) > queue_data['settings']['max_history_size']:
                queue_data['history'] = queue_data['history'][:queue_data['settings']['max_history_size']]
                
            # Remove from queue
            queue_data['queue'].pop(0)
            queue_data['active'] = False
            queue_data['current'] = None
            save_queue(queue_data)
            
            # Send notification to the Telegram user that download is complete
            # Include the user mention in the completion message
            completion_message = f'✅ Download complete: {title}'
            if user_mention:
                completion_message += f'\nRequested by {user_mention}'
            
            await bot.send_message(chat_id=user_id, text=completion_message)
            
        except Exception as e:
            print(f"Error processing queue item: {e}")
            
            # Send error notification to the user
            await bot.send_message(chat_id=user_id, text=f'❌ Error downloading: {str(e)}')
            
            # Mark as inactive so queue can continue
            queue_data = load_queue()
            queue_data['active'] = False
            queue_data['current'] = None
            queue_data['queue'].pop(0)  # Remove failed item
            save_queue(queue_data)
        
        finally:
            is_downloading = False

# Modify this to work with the queue system
async def download_from_queue(url):
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
            track_info = ydl.extract_info(url, download=True)
            track_title = track_info['title']
            converted_path = save_path + '/' + track_title + '.mp3'
            file_time = time.time()
            os.utime(converted_path, (file_time, file_time))
            return track_title, converted_path
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, download_task)
  
async def queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if user is authorized
    if user_id not in admins and user_id not in users:
        await update.message.reply_text('Sorry, you are not authorized to use this command.')
        return
    
    queue_data = load_queue()
    queue_length = len(queue_data['queue'])
    
    if queue_data['active']:
        current = queue_data['current']
        current_url = current['url']
        message = f"🔄 Currently downloading: {current_url}\n"
    else:
        message = "🔄 No active downloads.\n"
    
    message += f"📋 Queue length: {queue_length}\n"
    
    if queue_length > 0:
        message += "\nPending downloads:\n"
        for i, item in enumerate(queue_data['queue']):
            message += f"{i+1}. {item['url']}\n"
    
    await update.message.reply_text(message)

