"""Download your most recent CS2 Rush replay using your normal, signed-in Chrome.

Workflow:
  1. Opens your Rush match-history page in your everyday Chrome (with
     #autodownload on the end of the URL).
  2. The companion extension (./extension) sees that flag, takes the
     "Download GOTV Replay" link for the most recent match and downloads it
     into your Downloads folder.
  3. This script waits for the .dem.bz2 to land, decompresses it, and puts the
     .dem in your CS2 folder so you can run `playdemo <name>` in the console.

One-time setup:
  chrome://extensions -> enable Developer mode -> Load unpacked -> pick the
  `extension` folder next to this script. Do it in the Chrome profile that's
  signed into Steam.

Usage:
    python download_latest_rush_replay.py --steam-id 7656119XXXXXXXXXX   # or set STEAM_ID once
    python download_latest_rush_replay.py --profile "Profile 1"   # if Steam is in a non-default profile
    python download_latest_rush_replay.py --dest replays          # use game\\csgo\\replays instead
"""

import argparse
import bz2
import os
import re
import shutil
import subprocess
import sys
import time
import winreg
from pathlib import Path

RUSH_URL = "https://steamcommunity.com/profiles/{steam_id}/gcpd/730/?tab=matchhistoryrush#autodownload"
DOWNLOADS_DIR = Path.home() / "Downloads"
CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
]


def find_chrome() -> Path:
    for path in CHROME_CANDIDATES:
        if path.exists():
            return path
    sys.exit("Couldn't find chrome.exe.")


def find_csgo_dir() -> Path:
    """Locate <Steam library>/steamapps/common/Counter-Strike Global Offensive/game/csgo."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
        steam_path = Path(winreg.QueryValueEx(key, "SteamPath")[0])

    libraries = [steam_path]
    vdf = steam_path / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        libraries += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text())]

    for lib in libraries:
        csgo = lib / "steamapps" / "common" / "Counter-Strike Global Offensive" / "game" / "csgo"
        if csgo.is_dir():
            return csgo
    sys.exit("Couldn't find the CS2 install folder in any Steam library.")


def wait_for_archive(started: float, timeout: int) -> Path:
    """Wait for a .dem.bz2 in Downloads that was written after `started` and is finished."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        fresh = [p for p in DOWNLOADS_DIR.glob("*.dem.bz2") if p.stat().st_mtime >= started - 1]
        if fresh:
            newest = max(fresh, key=lambda p: p.stat().st_mtime)
            # Chrome writes to a .crdownload file first, then renames, so a
            # present .dem.bz2 is complete once its size stops changing.
            size = newest.stat().st_size
            time.sleep(1)
            if newest.stat().st_size == size and size > 0:
                return newest
        time.sleep(1)
    sys.exit(
        f"No replay showed up in {DOWNLOADS_DIR} within {timeout}s.\n"
        "Check the Chrome tab: the extension shows a status box in the top right.\n"
        "Make sure the extension is loaded in the profile that's signed into Steam (see --profile)."
    )


def extract(archive: Path, dest_dir: Path) -> Path:
    dem = dest_dir / archive.name.removesuffix(".bz2")
    tmp = dem.with_suffix(".dem.part")
    with bz2.open(archive, "rb") as src, open(tmp, "wb") as out:
        shutil.copyfileobj(src, out, length=1 << 20)
    tmp.replace(dem)
    return dem


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--steam-id", default=os.environ.get("STEAM_ID"),
                   help="your 17-digit SteamID64 (or set STEAM_ID); find it at https://steamid.io")
    p.add_argument("--profile", help='Chrome profile folder name, e.g. "Default" or "Profile 1" (default: last used)')
    p.add_argument("--dest", choices=["csgo", "replays"], default="csgo",
                   help="csgo = game\\csgo (playdemo <name>); replays = game\\csgo\\replays (in-game downloads folder)")
    p.add_argument("--timeout", type=int, default=300, help="seconds to wait for the download (default: 300)")
    p.add_argument("--keep-archive", action="store_true", help="leave the .dem.bz2 in Downloads after extracting")
    args = p.parse_args()

    if not args.steam_id:
        p.error("provide --steam-id or set STEAM_ID")

    csgo = find_csgo_dir()
    dest_dir = csgo / "replays" if args.dest == "replays" else csgo
    dest_dir.mkdir(exist_ok=True)

    cmd = [str(find_chrome())]
    if args.profile:
        cmd.append(f"--profile-directory={args.profile}")
    cmd.append(RUSH_URL.format(steam_id=args.steam_id))

    started = time.time()
    print("Opening the Rush match history in Chrome...")
    subprocess.Popen(cmd)

    archive = wait_for_archive(started, args.timeout)
    print(f"Downloaded: {archive}")

    dem = extract(archive, dest_dir)
    if not args.keep_archive:
        archive.unlink()
    print(f"Demo ready: {dem}")
    print(f"In CS2 console: playdemo {dem.relative_to(csgo).with_suffix('').as_posix()}")


if __name__ == "__main__":
    main()
