# CS2 Rush Replay Downloader

Grab the replay (GOTV demo) of your most recent Counter-Strike 2 **Rush** match with one command, and drop it straight into your CS2 folder ready to watch.

Steam only shows Rush replays on your "Personal Game Data" match-history page, and Valve serves them over plain HTTP, so Chrome blocks them as insecure downloads. This project uses a small Chrome extension that runs in your normal, signed-in Chrome to download the replay cleanly, plus a Python script that drives it and unpacks the demo.

## Requirements

- Windows, with CS2 installed through Steam
- Google Chrome, signed into steamcommunity.com
- Python 3.9+ (standard library only)

## Setup (one time)

1. **Load the extension.** Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, and pick the `extension` folder. Use the Chrome profile that's signed into Steam.
2. **Find your SteamID64**, the 17-digit number starting with `7656119`, for example at [steamid.io](https://steamid.io).
3. **Save it** so you don't have to type it every time (PowerShell):

   ```powershell
   [Environment]::SetEnvironmentVariable("STEAM_ID", "7656119XXXXXXXXXX", "User")
   ```

   Open a new terminal afterwards. You can also pass `--steam-id` on each run instead.

## Usage

```
python download_latest_rush_replay.py
```

Chrome opens your Rush match history, the extension downloads the newest replay, and the script unpacks it into `...\Counter-Strike Global Offensive\game\csgo`. It then prints the console command to watch it, for example:

```
playdemo 003847461463585194093_0227333902
```

Options:

| Flag | What it does |
| --- | --- |
| `--steam-id ID` | Your SteamID64 (defaults to the `STEAM_ID` environment variable) |
| `--profile "Profile 1"` | Chrome profile folder to use, if Steam isn't signed in under your default profile |
| `--dest replays` | Save into `game\csgo\replays` instead of `game\csgo` |
| `--keep-archive` | Keep the `.dem.bz2` in Downloads after unpacking |
| `--timeout N` | Seconds to wait for the download (default 300) |

The extension only acts when the page URL ends in `#autodownload`, which the script adds. Browsing your match history normally never triggers a download. While it runs, a status box in the top-right of the Steam tab shows what it's doing.

## Alternative: cookie-based bulk download

`download_rush_replays.py` downloads **every** replay still available on your Rush tab without opening Chrome. It authenticates with your `steamLoginSecure` cookie (from DevTools → Application → Cookies on steamcommunity.com):

```
set STEAM_LOGIN_SECURE=<cookie value>
python download_rush_replays.py --out rush_demos
```

It needs the `requests` package (`pip install requests`). Treat that cookie like a password: it gives full access to your Steam account.

## Notes

- Valve keeps replays for roughly 30 days. Older matches show no download link.
- Nothing is sent anywhere except Steam and Valve's replay servers.
