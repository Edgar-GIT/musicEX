from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import platform
import shutil
import subprocess


CONFIG_FILE = Path(__file__).with_name("musicex_config.json")
MAX_BATCH_DOWNLOADS = 4
YTDLP_FRAGMENT_THREADS = 8


def run_command(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception:
        return False


def has_command(command_name: str) -> bool:
    return shutil.which(command_name) is not None


def load_config() -> dict[str, str]:
    if not CONFIG_FILE.is_file():
        return {}

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    config: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str):
            config[key] = value

    return config


def save_config(config: dict[str, str]) -> bool:
    try:
        CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def normalize_path(path: Path) -> Path:
    return path.expanduser().resolve()


def get_default_download_dir(config: dict[str, str]) -> Path | None:
    folder_path = config.get("default_download_dir", "").strip()
    if not folder_path:
        return None

    return normalize_path(Path(folder_path))


def get_ytdlp_executable() -> str:
    local_bin = Path.home() / ".local" / "bin" / "yt-dlp"
    if local_bin.is_file():
        return str(local_bin)

    system_bin = shutil.which("yt-dlp")
    if system_bin:
        return system_bin

    return "yt-dlp"


def safe_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name).strip()
    return cleaned or "music"


def read_os_release() -> dict[str, str]:
    os_release_path = Path("/etc/os-release")
    if not os_release_path.is_file():
        return {}

    data: dict[str, str] = {}
    try:
        for line in os_release_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            data[key] = value.strip().strip('"').strip("'")
    except Exception:
        return {}

    return data


def detect_platform_info() -> dict[str, str]:
    system_name = platform.system().lower()
    info = {
        "system": system_name,
        "family": system_name or "unknown",
        "label": platform.system() or "Unknown",
    }

    if system_name == "windows":
        info["family"] = "windows"
        info["label"] = "Windows"
        return info

    if system_name == "darwin":
        info["family"] = "macos"
        info["label"] = "macOS"
        return info

    if system_name != "linux":
        return info

    os_release = read_os_release()
    distro_id = os_release.get("ID", "").lower()
    distro_like = os_release.get("ID_LIKE", "").lower().split()
    distro_name = os_release.get("PRETTY_NAME") or os_release.get("NAME") or "Linux"
    candidates = [distro_id] + distro_like

    family = "linux"
    if any(name in candidates for name in {"ubuntu", "debian", "linuxmint", "pop", "elementary", "zorin", "kali", "neon", "raspbian"}):
        family = "debian"
    elif any(name in candidates for name in {"arch", "manjaro", "endeavouros", "garuda"}):
        family = "arch"
    elif any(name in candidates for name in {"fedora", "rhel", "centos", "rocky", "alma", "ol", "amzn"}):
        family = "redhat"
    elif any(name in candidates for name in {"opensuse", "suse"}):
        family = "suse"
    elif has_command("apt-get"):
        family = "debian"
    elif has_command("pacman"):
        family = "arch"
    elif has_command("dnf") or has_command("yum"):
        family = "redhat"
    elif has_command("zypper"):
        family = "suse"

    info["family"] = family
    info["label"] = distro_name
    return info


def get_package_names(package_key: str) -> dict[str, str]:
    packages = {
        "yt-dlp": {
            "system": "yt-dlp",
            "winget": "yt-dlp.yt-dlp",
            "choco": "yt-dlp",
            "brew": "yt-dlp",
        },
        "ffmpeg": {
            "system": "ffmpeg",
            "winget": "Gyan.FFmpeg",
            "choco": "ffmpeg",
            "brew": "ffmpeg",
        },
    }
    return packages.get(package_key, {"system": package_key, "winget": package_key, "choco": package_key, "brew": package_key})


def build_install_strategies(package_key: str, platform_info: dict[str, str]) -> list[tuple[str, list[list[str]]]]:
    package_names = get_package_names(package_key)
    system_package = package_names["system"]
    strategies: list[tuple[str, list[list[str]]]] = []
    seen_managers: set[str] = set()

    def add_strategy(manager: str, commands: list[list[str]]) -> None:
        if manager in seen_managers:
            return
        seen_managers.add(manager)
        strategies.append((manager, commands))

    family = platform_info["family"]
    system_name = platform_info["system"]

    if family == "windows":
        if has_command("winget"):
            add_strategy("winget", [["winget", "install", package_names["winget"]]])
        if has_command("choco"):
            add_strategy("choco", [["choco", "install", package_names["choco"], "-y"]])
        return strategies

    if family == "macos":
        if has_command("brew"):
            add_strategy("brew", [["brew", "install", package_names["brew"]]])
        return strategies

    if family == "debian" and has_command("apt-get"):
        add_strategy(
            "apt-get",
            [
                ["sudo", "apt-get", "update"],
                ["sudo", "apt-get", "install", "-y", system_package],
            ],
        )

    if family == "arch" and has_command("pacman"):
        add_strategy("pacman", [["sudo", "pacman", "-S", "--noconfirm", system_package]])

    if family == "redhat":
        if has_command("dnf"):
            add_strategy("dnf", [["sudo", "dnf", "install", "-y", system_package]])
        if has_command("yum"):
            add_strategy("yum", [["sudo", "yum", "install", "-y", system_package]])

    if family == "suse" and has_command("zypper"):
        add_strategy(
            "zypper",
            [["sudo", "zypper", "--non-interactive", "install", system_package]],
        )

    if system_name == "linux":
        if has_command("apt-get"):
            add_strategy(
                "apt-get",
                [
                    ["sudo", "apt-get", "update"],
                    ["sudo", "apt-get", "install", "-y", system_package],
                ],
            )
        if has_command("pacman"):
            add_strategy("pacman", [["sudo", "pacman", "-S", "--noconfirm", system_package]])
        if has_command("dnf"):
            add_strategy("dnf", [["sudo", "dnf", "install", "-y", system_package]])
        if has_command("yum"):
            add_strategy("yum", [["sudo", "yum", "install", "-y", system_package]])
        if has_command("zypper"):
            add_strategy(
                "zypper",
                [["sudo", "zypper", "--non-interactive", "install", system_package]],
            )

    return strategies


def install_package(package_key: str, display_name: str, platform_info: dict[str, str]) -> bool:
    strategies = build_install_strategies(package_key, platform_info)
    if not strategies:
        return False

    print(
        f"Detected platform: {platform_info['label']} "
        f"({platform_info['family']}-based)."
    )

    for manager, commands in strategies:
        print(f"Trying to install {display_name} using {manager}...")
        success = True
        for command in commands:
            if not run_command(command):
                success = False
                break
        if success:
            return True

    return False


def try_update_ytdlp() -> None:
    ytdlp_exec = get_ytdlp_executable()

    run_command([ytdlp_exec, "-U"])

    if platform.system().lower() == "linux" and has_command("pipx"):
        run_command(["pipx", "install", "--force", "yt-dlp"])


def ensure_ffmpeg() -> bool:
    if has_command("ffmpeg"):
        return True

    platform_info = detect_platform_info()
    print("FFmpeg is missing. Trying to install it automatically...")
    return install_package("ffmpeg", "FFmpeg", platform_info)


def ensure_dependencies() -> bool:
    if not has_command("yt-dlp") and not (Path.home() / ".local" / "bin" / "yt-dlp").is_file():
        platform_info = detect_platform_info()
        print("yt-dlp is missing. Trying to install it automatically...")
        installed = install_package("yt-dlp", "yt-dlp", platform_info)

        if (not installed) and platform_info["system"] == "linux" and has_command("pipx"):
            print("Trying to install yt-dlp using pipx...")
            installed = run_command(["pipx", "install", "yt-dlp"])

        if not installed:
            print("Failed to install 'yt-dlp' automatically.")
            print("Please install it manually and run the script again.")
            return False

    try_update_ytdlp()

    if not ensure_ffmpeg():
        print("Failed to install FFmpeg automatically.")
        print("Please install it manually and run the script again.")
        return False

    return True


def detect_cookie_browsers() -> list[str]:
    home = Path.home()
    system_name = platform.system().lower()

    if system_name == "linux":
        checks = {
            "firefox": home / ".mozilla" / "firefox",
            "chrome": home / ".config" / "google-chrome",
            "chromium": home / ".config" / "chromium",
            "brave": home / ".config" / "BraveSoftware" / "Brave-Browser",
            "edge": home / ".config" / "microsoft-edge",
        }
    elif system_name == "windows":
        local = Path.home() / "AppData" / "Local"
        roaming = Path.home() / "AppData" / "Roaming"
        checks = {
            "firefox": roaming / "Mozilla" / "Firefox",
            "chrome": local / "Google" / "Chrome",
            "chromium": local / "Chromium",
            "brave": local / "BraveSoftware" / "Brave-Browser",
            "edge": local / "Microsoft" / "Edge",
        }
    else:
        return []

    return [name for name, path in checks.items() if path.exists()]


def list_search_urls(ytdlp_exec: str, search_query: str) -> list[str]:
    cmd = [
        ytdlp_exec,
        "--flat-playlist",
        "--dump-single-json",
        search_query,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except Exception:
        return []

    urls: list[str] = []
    for entry in data.get("entries", []):
        if not isinstance(entry, dict):
            continue

        url = entry.get("webpage_url") or entry.get("url")
        if not isinstance(url, str) or not url.strip():
            continue

        if not url.startswith("http"):
            ie_key = (entry.get("ie_key") or "").lower()
            if "youtube" in ie_key or len(url) == 11:
                url = f"https://www.youtube.com/watch?v={url}"
            elif "soundcloud" in ie_key:
                url = f"https://soundcloud.com/{url.lstrip('/')}"
            else:
                continue

        urls.append(url)

    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)

    return unique_urls


def list_music_sources(ytdlp_exec: str, query: str) -> list[str]:
    if query.startswith(("http://", "https://")):
        return [query]

    searches = {
        "youtube": f"ytsearch8:{query}",
        "soundcloud": f"scsearch5:{query}",
    }
    results: dict[str, list[str]] = {name: [] for name in searches}

    with ThreadPoolExecutor(max_workers=len(searches)) as executor:
        futures = {
            executor.submit(list_search_urls, ytdlp_exec, search_query): name
            for name, search_query in searches.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                results[name] = []

    sources: list[str] = []
    seen: set[str] = set()
    for url in results["youtube"] + results["soundcloud"] + [query]:
        if url in seen:
            continue
        seen.add(url)
        sources.append(url)

    return sources


def download_with_profiles(
    ytdlp_exec: str,
    target: str,
    output_template: str,
    cookie_browser: str | None,
) -> bool:
    common = [
        ytdlp_exec,
        "--no-playlist",
        "--force-ipv4",
        "--geo-bypass",
        "--retries",
        "5",
        "--fragment-retries",
        "5",
        "--concurrent-fragments",
        str(YTDLP_FRAGMENT_THREADS),
        "--newline",
        "--embed-metadata",
        "--embed-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--extractor-args",
        "youtube:player_client=web,mweb,android,ios,tv",
    ]

    if cookie_browser:
        common += ["--cookies-from-browser", cookie_browser]

    profiles = [
        [
            "-f",
            "bestaudio[ext=m4a]/ba[ext=m4a]/best[ext=mp4]",
            "--merge-output-format",
            "mp4",
        ],
        [
            "-f",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "m4a",
        ],
        [
            "-f",
            "bestaudio/best",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "192K",
        ],
    ]

    for profile in profiles:
        cmd = common + profile + ["-o", output_template, target]
        try:
            subprocess.run(cmd, check=True)
            return True
        except Exception:
            continue

    return False


def download_music(query: str, download_dir: Path) -> None:
    download_dir.mkdir(parents=True, exist_ok=True)
    file_base_name = safe_filename(query)
    output_template = str(download_dir / f"{file_base_name}.%(ext)s")
    ytdlp_exec = get_ytdlp_executable()
    targets = list_music_sources(ytdlp_exec, query)

    cookie_browsers = detect_cookie_browsers()
    cookie_options: list[str | None] = [None] + cookie_browsers

    for target in targets:
        print(f"Trying source: {target}")
        for browser in cookie_options:
            if browser:
                print(f"Trying browser cookies from: {browser}")
            if download_with_profiles(ytdlp_exec, target, output_template, browser):
                return

    raise RuntimeError(
        "All download attempts failed. Update yt-dlp and try a different search."
    )


def prompt_manual_download_dir() -> Path | None:
    folder_path = input("Enter the folder path: ").strip()
    if not folder_path:
        print("Invalid folder path.")
        return None

    return normalize_path(Path(folder_path))


def prompt_new_download_dir(initial_dir: Path | None = None) -> Path | None:
    _ = initial_dir

    while True:
        print()
        print("Choose how to set the download folder")
        print("1. Enter a folder path manually")
        print("2. Cancel")

        option = input("Choose an option: ").strip()

        if option == "1":
            selected = prompt_manual_download_dir()
            if selected is not None:
                return selected
            print("Please enter a valid folder path.")
            continue

        if option == "2":
            return None

        print("Invalid option. Please choose 1 or 2.")


def prompt_download_dir(config: dict[str, str]) -> Path | None:
    default_dir = get_default_download_dir(config)

    if default_dir is None:
        print("No default download folder is set.")
        return prompt_new_download_dir()

    while True:
        print()
        print(f"Default download folder: {default_dir}")
        print("1. Use the default folder")
        print("2. Use a new folder")
        print("3. Cancel")

        option = input("Choose an option: ").strip()

        if option == "1":
            return default_dir

        if option == "2":
            return prompt_new_download_dir(default_dir)

        if option == "3":
            return None

        print("Invalid option. Please choose 1, 2, or 3.")


def set_default_music_path(config: dict[str, str]) -> None:
    current_default = get_default_download_dir(config)

    print()
    print("Default music folder")
    if current_default is None:
        print("Current default folder: not set")
    else:
        print(f"Current default folder: {current_default}")

    while True:
        print("1. Enter a folder path manually")
        print("2. Clear the default folder")
        print("3. Back to the main menu")

        option = input("Choose an option: ").strip()

        if option == "1":
            selected = prompt_manual_download_dir()
            if selected is None:
                print("Please enter a valid folder path.")
                continue
        elif option == "2":
            config.pop("default_download_dir", None)
            if save_config(config):
                print("Default folder cleared.")
            else:
                print("Could not save the configuration file.")
            return
        elif option == "3":
            return
        else:
            print("Invalid option. Please choose 1, 2, or 3.")
            continue

        config["default_download_dir"] = str(selected)
        if save_config(config):
            print(f"Default folder saved: {selected}")
        else:
            print("Could not save the configuration file.")
        return


def download_single_song(config: dict[str, str]) -> None:
    music_name = input("Enter the song name or URL: ").strip()
    if not music_name:
        print("Invalid song name.")
        return

    download_dir = prompt_download_dir(config)
    if download_dir is None:
        return

    try:
        print("Starting download...")
        download_music(music_name, download_dir)
        print(f"Download completed in: {download_dir}")
    except Exception as exc:
        print(f"Download error: {exc}")


def collect_multiple_songs() -> list[str]:
    print("Enter one song name or URL per line.")
    print("Type 0 when you are finished.")

    songs: list[str] = []
    while True:
        music_name = input("Song: ").strip()
        if music_name == "0":
            break
        if not music_name:
            print("Please enter a song name, a URL, or 0 to finish.")
            continue
        songs.append(music_name)

    return songs


def download_multiple_songs(config: dict[str, str]) -> None:
    songs = collect_multiple_songs()
    if not songs:
        print("No songs were provided.")
        return

    download_dir = prompt_download_dir(config)
    if download_dir is None:
        return

    total = len(songs)
    workers = min(MAX_BATCH_DOWNLOADS, total)
    print(f"Using up to {workers} parallel downloads.")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for index, song in enumerate(songs, start=1):
            print(f"Queued download {index}/{total}: {song}")
            future = executor.submit(download_music, song, download_dir)
            futures[future] = (index, song)

        for future in as_completed(futures):
            index, song = futures[future]
            try:
                future.result()
                print(f"Finished download {index}/{total}: {song}")
            except Exception as exc:
                print(f"Download error for '{song}': {exc}")

    print(f"Batch download finished. Files were saved in: {download_dir}")


def show_menu(config: dict[str, str]) -> None:
    default_dir = get_default_download_dir(config)

    print()
    print("Music Downloader")
    if default_dir is None:
        print("Default folder: not set")
    else:
        print(f"Default folder: {default_dir}")
    print("1. Download one song")
    print("2. Download multiple songs")
    print("3. Set default music path")
    print("4. Exit")


def main() -> None:
    if not ensure_dependencies():
        return

    config = load_config()

    while True:
        show_menu(config)
        option = input("Choose an option: ").strip()

        if option == "1":
            download_single_song(config)
        elif option == "2":
            download_multiple_songs(config)
        elif option == "3":
            set_default_music_path(config)
        elif option == "4":
            print("Goodbye.")
            return
        else:
            print("Invalid option. Please choose 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
