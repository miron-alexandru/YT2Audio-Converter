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

class YouTubeConverter:
    """GUI application for downloading YouTube videos and playlists in MP3 format."""

    def __init__(self):
        self.download_directory = os.getcwd()
        self.stop_event = threading.Event()
        self.window = tk.Tk()
        self.window.geometry("610x230")
        self.window.config(bg="#0D47A1")
        self.window.resizable(width=False, height=False)
        self.window.title("YouTube to MP3 Converter")
        self.window.iconbitmap("icon.ico")
        self.link = tk.StringVar()
        self.progress_bar = ttk.Progressbar(self.window, length=200, mode="determinate")
        self.link_enter = None
        self.download_location_button = None
        self.stop_button = None
        self.download_button = None

    def run(self):
        """Start the GUI application."""
        self._create_ui()
        self.window.mainloop()

    def _create_ui(self):
        """Create the user interface"""
        tk.Label(
            self.window,
            text="Progress:",
            font="Arial 15 bold",
            fg="white",
            bg="#0D47A1",
        ).place(x=10, y=140)
        tk.Label(
            self.window,
            text="YouTube Video and Playlist Converter",
            font="Arial 25 bold",
            fg="white",
            bg="#0D47A1",
        ).pack(pady=10)
        tk.Label(
            self.window,
            text="Paste YouTube link here:",
            font="Arial 15 bold",
            fg="white",
            bg="#0D47A1",
        ).place(x=5, y=60)
        self.link_enter = tk.Entry(
            self.window,
            width=53,
            textvariable=self.link,
            font="Arial 15 bold",
            bg="white",
        )
        self.link_enter.place(x=5, y=100)
        self.progress_bar.place(x=110, y=145)
        style = ttk.Style()
        style.configure(
            "TButton",
            font=("Arial", 13),
            foreground="black",
            background="#1565C0",
            padding=2,
            borderwidth=0,
        )
        self.download_location_button = ttk.Button(
            self.window,
            text="Download Location",
            style="TButton",
            command=self._choose_download_directory,
        )
        self.download_location_button.place(x=10, y=180)
        self.stop_button = ttk.Button(
            self.window, text="Stop", style="TButton", command=self._stop_downloading
        )
        self.stop_button.place(x=480, y=140)
        self.download_button = ttk.Button(
            self.window, text="Start", style="TButton", command=self._download_video
        )
        self.download_button.place(x=340, y=140)
        self.download_button.config(
            command=lambda: threading.Thread(
                target=self._download_video, args=(), daemon=True
            ).start()
        )

    def _download_video(self):
        self.stop_event.clear()
        yt_link = str(self.link.get())
        is_playlist = False
        # Check if the link is a playlist or a single video link
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
            return

        def convert_to_mp3(video_file_path, audio_file_path):
            if hasattr(sys, "_MEIPASS"):
                # Running as a PyInstaller bundle
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
                    video_title_match = re.search(r'(.+) - YouTube', title)
                    if video_title_match:
                        video_title = video_title_match.group(1)
                        return video_title
                    else:
                        return None
                else:
                    return None
            except Exception as e:
                return None

        # Define a function for downloading a single video
        def download_single_video(video_url):
            video_title = ""
            try:
                if self.stop_event.is_set():
                    return None, None
                video = YouTube(video_url)
                audio_stream = (
                    video.streams.filter(only_audio=True).order_by("abr").desc().first()
                )
                if audio_stream:
                    try:
                        video_name = get_video_title(video_url)
                        title_to_use = video_name if video_name else video.title
                    except Exception as e:
                        title_to_use = video.title

                    file_name = re.sub("[^A-Za-z0-9 -]+", "", title_to_use) + ".mp4"
                    video_file_path = os.path.join(self.download_directory, file_name)
                    audio_file_path = f"{os.path.splitext(video_file_path)[0]}.mp3"

                    # Download the video file
                    audio_stream.download(
                        output_path=self.download_directory, filename=file_name
                    )

                    # Convert video to MP3 using ffmpeg
                    success = convert_to_mp3(video_file_path, audio_file_path)
                    if not success:
                        raise Exception("Failed to convert video to MP3.")
                    os.remove(video_file_path)

                return video_title, None  # Success
            except Exception as ex:
                return video_title, str(ex)  # Failure

        if is_playlist:
            max_workers = 3
        else:
            max_workers = 1

        # Download the video or the playlist using multi-threading
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(num_videos):
                if self.stop_event.is_set():
                    break
                if is_playlist:
                    video_url = purl.video_urls[i]
                else:
                    video_id = video_id_match[1]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                futures.append(executor.submit(download_single_video, video_url))

            # Monitor the progress of the downloads
            completed_count = 0
            for future in concurrent.futures.as_completed(futures):
                video_title, error_message = future.result()
                completed_count += 1
                if error_message:
                    if "[WinError 32]" or ["WinError 2"] in error_message:
                        continue
                    else:
                        messagebox.showerror(
                            "Error",
                            f"Failed to download: {video_title}\nError: {error_message}",
                        )
                self.progress_bar["value"] = int(completed_count / num_videos * 100)
                self.window.update()
                self.window.update_idletasks()

        self.progress_bar["value"] = 0
        success_label = tk.Label(
            self.window,
            text="",
            font="arial 19",
            fg="white",
            bg="#0D47A1",
            highlightthickness=0,
        )
        success_label.place(x=170, y=178)
        success_label.config(text="Success!")
        success_label.after(5000, success_label.config, {"text": ""})


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