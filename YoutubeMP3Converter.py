"""
GUI application that can convert YouTube videos or playlists to MP3 format,
and download them to a specified directory.

Author: [Miron Alexandru]
"""

import os
import sys
from bs4 import BeautifulSoup
import re
import requests
import threading
import concurrent.futures
import subprocess
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import tkinter.messagebox as messagebox
from pytubefix import YouTube
from pytube import Playlist

def resource_path(relative_path):
    """ Get the absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class YouTubeConverter:
    """GUI application for downloading YouTube videos and playlists in MP3 format."""

    def __init__(self):
        self.download_directory = os.getcwd()
        self.stop_event = threading.Event()
        self.window = tk.Tk()
        self.window.geometry("710x290")
        self.window.config(bg="#1E1E2F")
        self.window.resizable(False, False)
        self.window.title("YouTube to MP3 Converter")
        self.window.iconbitmap(resource_path("icon.ico"))
        self.link = tk.StringVar()
        self.progress_bar = ttk.Progressbar(self.window, length=400, mode="determinate")
        self.link_enter = None
        self.download_location_button = None
        self.stop_button = None
        self.download_button = None
        self.status_label = None

    def run(self):
        """Start the GUI application."""
        self._create_ui()
        self.window.mainloop()

    def _create_ui(self):
        """Create the user interface"""
        tk.Label(
            self.window,
            text="YouTube MP3 Converter",
            font=("Helvetica", 22, "bold"),
            fg="#FFFFFF",
            bg="#1E1E2F"
        ).pack(pady=15)

        frame = tk.Frame(self.window, bg="#1E1E2F", width=550)
        frame.pack(pady=5)

        tk.Label(
            frame,
            text="YouTube Link:",
            font=("Helvetica", 14),
            fg="#FFFFFF",
            bg="#1E1E2F"
        ).grid(row=0, column=0, sticky="w", padx=5,)

        self.link_enter = tk.Entry(
            frame,
            width=50,
            textvariable=self.link,
            font=("Helvetica", 14),
            bg="#FFFFFF",
            relief="flat"
        )
        #self.link_enter.grid(row=0, column=1, padx=5)
        self.link_enter.grid(row=0, column=1, padx=(5, 40))

        progress_frame = tk.Frame(self.window, bg="#1E1E2F")
        progress_frame.pack(pady=10)

        tk.Label(
            progress_frame,
            text="Progress:",
            font=("Helvetica", 14),
            fg="#FFFFFF",
            bg="#1E1E2F"
        ).pack(anchor="w", padx=10)

        self.progress_bar.pack(pady=5)

        button_frame = tk.Frame(self.window, bg="#1E1E2F")
        button_frame.pack(pady=15)

        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "TButton",
            font=("Helvetica", 12),
            padding=6,
            background="#5E81AC",
            foreground="black"
        )

        self.download_location_button = ttk.Button(
            button_frame,
            text="Choose Download Folder",
            command=self._choose_download_directory
        )
        self.download_location_button.grid(row=0, column=0, padx=10)

        self.download_button = ttk.Button(
            button_frame,
            text="Start Download",
            command=lambda: threading.Thread(
                target=self._download_video, daemon=True
            ).start()
        )
        self.download_button.grid(row=0, column=1, padx=10)

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop",
            command=self._stop_downloading
        )
        self.stop_button.grid(row=0, column=2, padx=10)

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="",
            font=("Helvetica", 14),
            fg="#FACC15",
            bg="#1E1E2F"
        )
        self.status_label.pack(pady=5)

    def _download_video(self):
        self.stop_event.clear()
        self.status_label.config(text="Downloading...", fg="#FACC15")
        yt_link = str(self.link.get())
        is_playlist = False

        video_id_match = re.match(
            r"https?://(?:www\.|)youtu(?:be\.com|\.be)/(?:watch\?.*?v=|)([^\s&]+)",
            yt_link,
        )
        playlist_id_match = re.match(
            r"https?://(?:www\.|)youtube\.com/(?:watch\?.*?&|)list=([^\s&]+)|"
            r"https?://youtu\.be/[^\s?]+(?:\?|&)list=([^\s&]+)|"
            r"https?://(?:www\.|)youtube\.com/playlist\?list=([^\s&]+)",
            yt_link,
        )

        if playlist_id_match:
            purl = Playlist(yt_link)
            num_videos = len(purl.video_urls)
            is_playlist = True
        elif video_id_match:
            num_videos = 1
        else:
            messagebox.showerror("Error", "Invalid link")
            self.status_label.config(text="", fg="#FACC15")
            return

        def convert_to_mp3(video_file_path, audio_file_path):
            if hasattr(sys, "_MEIPASS"):
                ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg", "bin", "ffmpeg.exe")
            else:
                ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg\\bin\\ffmpeg.exe")
            try:
                subprocess.run(
                    [
                        ffmpeg_path,
                        "-y",
                        "-i",
                        video_file_path,
                        "-vn",
                        "-acodec",
                        "libmp3lame",
                        audio_file_path,
                    ],
                    check=True,
                    shell=True
                )
                return True
            except FileNotFoundError:
                return "ffmpeg executable not found"
            except subprocess.SubprocessError as ex:
                return f"Subprocess error: {str(ex)}"
            except OSError as ex:
                return f"OS error: {str(ex)}"
            except Exception as ex:
                return f"Unexpected error: {str(ex)}"

        def get_video_title(video_url):
            try:
                response = requests.get(video_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title = soup.find('title').text
                    match = re.search(r'(.+) - YouTube', title)
                    return match.group(1) if match else None
                return None
            except:
                return None

        def download_single_video(video_url):
            video_title = ""
            try:
                if self.stop_event.is_set():
                    return None, None
                video = YouTube(video_url)
                audio_stream = video.streams.filter(only_audio=True).order_by("abr").desc().first()
                if audio_stream:
                    try:
                        video_name = get_video_title(video_url)
                        title_to_use = video_name if video_name else video.title
                    except:
                        title_to_use = video.title

                    file_name = re.sub("[^A-Za-z0-9 -]+", "", title_to_use) + ".mp4"
                    video_file_path = os.path.join(self.download_directory, file_name)
                    audio_file_path = f"{os.path.splitext(video_file_path)[0]}.mp3"

                    audio_stream.download(output_path=self.download_directory, filename=file_name)

                    success = convert_to_mp3(video_file_path, audio_file_path)
                    if not success:
                        raise Exception("Failed to convert video to MP3.")
                    os.remove(video_file_path)

                return video_title, None
            except Exception as ex:
                return video_title, str(ex)

        max_workers = 3 if is_playlist else 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(num_videos):
                if self.stop_event.is_set():
                    self.status_label.config(text="Download Stopped", fg="#EF4444")
                    self.progress_bar["value"] = 0
                    self.window.update()
                    return
                if is_playlist:
                    video_url = purl.video_urls[i]
                else:
                    video_id = video_id_match[1]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                futures.append(executor.submit(download_single_video, video_url))

            completed_count = 0
            for future in concurrent.futures.as_completed(futures):
                video_title, error_message = future.result()
                completed_count += 1
                if error_message:
                    if "[WinError 32]" or "[WinError 2]" in error_message:
                        continue
                    else:
                        messagebox.showerror("Error", f"Failed: {video_title}\n{error_message}")
                self.progress_bar["value"] = int(completed_count / num_videos * 100)
                self.window.update()
                self.window.update_idletasks()

        self.progress_bar["value"] = 0
        self.status_label.config(text="Download Complete!", fg="#A3E635")
        self.window.after(5000, lambda: self.status_label.config(text=""))

    def _choose_download_directory(self):
        """Choose the download directory"""
        self.download_directory = filedialog.askdirectory(
            initialdir="/", title="Select download directory"
        )

    def _stop_downloading(self):
        self.stop_event.set()

if __name__ == "__main__":
    converter = YouTubeConverter()
    converter.run()