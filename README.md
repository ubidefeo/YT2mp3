# YT2mp3: a Telegram Bot

## Download YouTube videos as mp3

This Telegram Bot's main reason to exist is to receive YouTube videos and playlists' URLs and export them to mp3 files into a designated folder.
Very useful to turn your favourite YT shows into downloaded podcasts (where watching is not required).
How you play them back is out of the scope of this script.

Since it depends on the correct functioning of `yt-dlp`, if you get errors make sure your yt-dlp is up-to-date.

![chat](images/YT2mp3_screenshots.png)

## Requirements

* [create your Telegram Bot](https://core.telegram.org/bots/tutorial) first.
* Terminal shell (works on Mac OS and Linux, Windows sounds like a "you" problem)
* [Poetry](https://python-poetry.org/docs/#installing-with-pipx)
* Python3
* Pip3

__Poetry will install all the requirements in its own environment.__


## Installation

Clone the repository
```bash
git clone https://github.com/ubidefeo/YT2mp3.git
cd YT2mp3
```

### Continue with Poetry (recommended)

#### Install dependencies

```shell
poetry install
```

#### *or*

#### Using regular Python

Make sure you are running Python 3 and pip.

```shell
> python --version
Python 3.11.2

> pip --version
pip 25.0.1
```

Depending on how the commands are aliased on your system you may have to run them in different ways.

e.g.:

```shell
pip install -r requirements.txt
```

vs

```shell
pip3 install -r requirements.txt
```

## Configure

### Create a tg_token.py file with your bot token
echo "TG_TOKEN = 'your-bot-token-here'" > YT2mp3/tg_token.py

#### Create an authorised_users.yml file
cp YT2mp3/config/default_config.yml authorised_users.yml
cp YT2mp3/config/tg_token_example.py tg_token.py

### Edit authorised_users.yml and tg_token.py to add your user(s) ID(s) and your Telegram token

## Usage

### Poetry

```shell
poetry run ytmp3
```

### Regular Python

```shell
chmod +x yt2mp3.py
./yt2mp3.py
```

If everything worked well you can start sending messages to your bot and get it to download mp3 of any YT video for you.

## Commands

* *`/help`* - Show this help message
* *`/hello`* - Greet the bot
* *`/myid`* - Get your user ID (send to admin to be allowed to download)
* *`/dl <url>`* - Download a YouTube video (or playlist)
* *`/skip`* - Skip the current download and continue to the next
* *`/stop`* - Stop the current download
* *`/current`* - Show the currently downloading item (with preview)
* *`/queue`* - Check the download queue status
* *`/purge`* - Clear the download queue (admins only)
* *`/test`* - Test the bot with a sample URL (admins only)
