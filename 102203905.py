import tkinter as tk
from tkinter import messagebox
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import zipfile
import os
import time
from pytube import YouTube
from pydub import AudioSegment
from googleapiclient.discovery import build
from credentials import password, email, api_key  


class VideoDownloader:
    def __init__(self, singer_name, num_videos):
        self.singer_name = singer_name
        self.num_videos = num_videos
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def search_videos(self):
        request = self.youtube.search().list(
            q=self.singer_name,
            part='id',
            type='video',
            maxResults=self.num_videos
        )
        response = request.execute()

        video_ids = [item['id']['videoId'] for item in response.get('items', [])]
        return [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]

    def download_videos(self):
        video_urls = self.search_videos()
        if not video_urls:
            raise ValueError("No videos found for the specified singer.")
        
        downloaded_files = []
        for url in video_urls:
            attempts = 3  
            for attempt in range(attempts):
                try:
                    yt = YouTube(url)
                    audio_stream = yt.streams.filter(only_audio=True).first()
                    if audio_stream is None:
                        print(f"No audio stream found for {url}.")
                        break
                    audio_file = audio_stream.download(filename=f"{yt.title}.mp4")
                    downloaded_files.append(audio_file)
                    break  # Exit retry loop if successful
                except Exception as e:
                    print(f"Error downloading {url}: {e}")
                    if attempt < attempts - 1:  
                        time.sleep(5)  
                    else:
                        print(f"Failed to download {url} after {attempts} attempts.")
            time.sleep(1)  
        return downloaded_files


class AudioProcessor:
    def __init__(self, downloaded_files, audio_duration):
        self.downloaded_files = downloaded_files
        self.audio_duration = audio_duration

    def cut_audio_files(self):
        cut_files = []
        for file in self.downloaded_files:
            try:
                audio = AudioSegment.from_file(file)
                cut_audio = audio[:self.audio_duration * 1000]  
                cut_file_name = f"cut_{os.path.basename(file)}"
                cut_audio.export(cut_file_name, format='mp3')
                cut_files.append(cut_file_name)
            except Exception as e:
                print(f"Error processing {file}: {e}")
        return cut_files

    def merge_audio_files(self, cut_files, output_file):
        combined = AudioSegment.empty()
        for file in cut_files:
            audio = AudioSegment.from_file(file)
            combined += audio
        combined.export(output_file, format='mp3')


class EmailSender:
    def __init__(self, email_address, email_password, smtp_server, smtp_port):
        self.email_address = email_address
        self.email_password = email_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_email(self, recipient_email, zip_filename):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = recipient_email
            msg['Subject'] = "Your Mashup File"

            with open(zip_filename, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(zip_filename))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(zip_filename)}"'
                msg.attach(part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False


class ZipFileCreator:
    @staticmethod
    def create_zip_file(output_file):
        zip_filename = 'output.zip'
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            zipf.write(output_file)
        return zip_filename


class Application:
    def __init__(self, master):
        self.master = master
        master.title("Mashup Audio Creator")

        # Heading
        heading = tk.Label(master, text="Song Mashup Creator", font=("Arial", 16, "bold"))
        heading.grid(row=0, columnspan=2, pady=10)

        # Input fields
        tk.Label(master, text="Singer Name:").grid(row=1, column=0, padx=10, pady=10)
        self.singer_entry = tk.Entry(master)
        self.singer_entry.grid(row=1, column=1)

        tk.Label(master, text="Number of Videos (> 10):").grid(row=2, column=0, padx=10, pady=10)
        self.num_videos_entry = tk.Entry(master)
        self.num_videos_entry.grid(row=2, column=1)

        tk.Label(master, text="Audio Duration (sec > 20):").grid(row=3, column=0, padx=10, pady=10)
        self.audio_duration_entry = tk.Entry(master)
        self.audio_duration_entry.grid(row=3, column=1)

        tk.Label(master, text="Email ID:").grid(row=4, column=0, padx=10, pady=10)
        self.email_entry = tk.Entry(master)
        self.email_entry.grid(row=4, column=1)

        # Create Send Email button
        send_button = tk.Button(master, text="Send Email", command=self.process_request, bg="green", fg="white", font=("Arial", 12, "bold"), width=15)
        send_button.grid(row=5, columnspan=2, pady=20)

    def process_request(self):
        singer_name = self.singer_entry.get()
        try:
            num_videos = int(self.num_videos_entry.get())
            audio_duration = int(self.audio_duration_entry.get())
            email = self.email_entry.get()
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numbers.")
            return

        if num_videos <= 10 or audio_duration <= 20:
            messagebox.showerror("Input Error", "Number of videos must be > 10 and duration > 20 seconds.")
            return

        # Process videos
        downloader = VideoDownloader(singer_name, num_videos)
        try:
            downloaded_files = downloader.download_videos()
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
            return

        if not downloaded_files:
            messagebox.showerror("Error", "No videos were downloaded. Please check the singer name and try again.")
            return

        # Process audio
        processor = AudioProcessor(downloaded_files, audio_duration)
        cut_files = processor.cut_audio_files()
        output_file = 'merged_audio.mp3'
        processor.merge_audio_files(cut_files, output_file)

        # Create zip file
        zip_filename = ZipFileCreator.create_zip_file(output_file)

        # Send email
        email_sender = EmailSender(
            email_address=email, 
            email_password=password, 
            smtp_server='smtp.gmail.com', 
            smtp_port=587 
        )
        if email_sender.send_email(email, zip_filename):
            messagebox.showinfo("Success", "Email sent successfully!")
        else:
            messagebox.showerror("Error", "Failed to send email.")


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()

