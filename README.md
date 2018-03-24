# zared
Zara price / stock tracking

## Requirements
This was written and tested with Anaconda Python 3.5.2 on macOS High Sierra.

It is not guaranteed to work anywhere else.

It is not guaranteed to work perfectly on Anaconda Python 3.5.2 / macOS High Sierra either.

## Setup

### Clone the repository
Follow GitHub's instructions above ^

### Set up which physical stores you want to check stocks for
1. Go to https://www.maxmind.com/en/locate-my-ip-address
2. Copy down your latitude/longitude from the "Approximate Coordinates" column
3. Go to https://www.zara.com/us/en/stores-locator/search?lat=[your_latitude_here]&lng=[your_longitude_here]&ajax=true, and save the file to your local repo root as `stores.json`, i.e. `cd [/path/to/zared] && curl https://www.zara.com/us/en/stores-locator/search?lat=[your_latitude_here]&lng=[your_longitude_here]&ajax=true -o stores.json`

### Set your system up to automatically check prices / stocks
See https://alvinalexander.com/mac-os-x/mac-osx-startup-crontab-launchd-jobs

For example,

1. Move `com.zared.updater.plist` from this repo into `~/Library/LaunchAgents/`
2. In `com.zared.updater.plist`, set your `EnvironmentVariable`s (if you need them), and replace `[/path/to/zared]` with the path to your local copy of this repository
3. In `updater.sh`, replace `[/path/to/zared]` with the path to your local copy of this repository
4. Do `launchctl load com.com.zared.updater.plist` to start the updater
4. Do `launchctl unload com.com.zared.updater.plist` if you want to stop the updater

## Usage

Add an item to track

```
python zared.py --url [url_to_zara_item_page]
```

Add an item to track, with a specific color

```
python zared.py --url [url_to_zara_item_page] --color [color_name]
```

Pull current prices and availabilities for all items currently being tracked

```
python zared.py --update --now
```

Pull updated prices and availabilities for all items currently being tracked, with a random delay

```
python zared.py --update
```


## Legal-ish Things

### Disclaimers and Liability Release
By using the code provided in this repository, you agree that the creators of and contributors to this repository will not be liable or held responsible for any loss of life, limb, property, or otherwise, or any effect, toward or untoward, concerning your financial, mental, moral, physical, metaphysical, etc. situation as a result of, or in correlation with, the usage of the contents of this repository.

Further, you agree that if you use this tool to programmatically make too many requests to the Zara website and get banned, sued, guillotined, stoned, or otherwise suffer repercussions at the invisible hand of Zara, the fault will be yours and yours alone.

TL;DR: Use at your own risk, and your risk alone.

### "License"
You are free to modify this for your own use.

You are not allowed to sell or exchange this for money / dogecoin / seashells / [insert over-hyped currency *du jour*].
