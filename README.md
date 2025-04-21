# YT2mp3: a Telegram Bot

## Download YouTube videos as mp3

This Telegram Bot will accept a `/url` command action followed by a YouTube URL, download the resource using `yt-dlp` and save an mp3 file to a designated folder.
Very useful to turn your favourite YT shows into downloaded podcasts (where watching is not required).
How you play them back is out of the scope of this script.

Since it depends on the correct functioning of `yt-dlp`, if you get errors make sure your yt-dlp is up-to-date.

![chat](images/YT2mp3_screenshots.png)

## Requirements

* [create your Telegram Bot](https://core.telegram.org/bots/tutorial) first.
* Terminal shell (works on Mac OS and Linux, Windows sounds like a "you" problem)
* Python3
* Pip3

## Installation

Make sure you are running Python 3 and pip.
Depending on how the commands are aliased on your system you may have to run them in different ways.

e.g.:

```shell
pip install -r requirements.txt
```

vs

```shell
pip3 install -r requirements.txt
```

## Usage

```shell
chmod +x downloader.py
./downloader.py
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
