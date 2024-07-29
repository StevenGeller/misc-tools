"""
YouTube Video Summarizer with Claude Opus API

This script takes a YouTube video URL, extracts the video ID, fetches the video details,
retrieves the transcript, and generates a summary using the Claude Opus API. The summary
and the full transcript are then saved to a text file.

Key functionalities include:
1. Extracting the YouTube video ID from various forms of URLs.
2. Fetching video details (title) using youtube_dl.
3. Retrieving the transcript of the video using YouTubeTranscriptApi.
4. Sending a request to Claude Opus API to generate a summary of the transcript.
5. Saving the video title, summary, and full transcript to a text file.
6. Logging for better tracking and debugging.
7. Configuration management via an external configuration file.

Usage:
    python script_name.py <YouTube Video URL>

Example:
    python script_name.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
"""

import os
import requests
import argparse
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs
import logging
from configparser import ConfigParser

# Configuration
CONFIG_FILE = 'config.ini'

def load_config(config_file):
    config = ConfigParser()
    config.read(config_file)
    return config

config = load_config(CONFIG_FILE)

CLAUDE_API_KEY = config.get('claude', 'api_key')
CLAUDE_API_URL = config.get('claude', 'api_url')

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_video_id(url):
    """Extract the video ID from various forms of YouTube URLs."""
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        if parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    logger.error("Could not extract video ID from URL")
    return None

def get_video_details(video_id):
    """Fetch video details using youtube_dl."""
    logger.info(f"Fetching details for video ID: {video_id}")
    ydl_opts = {}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        video_title = info.get('title', None)
    if video_title:
        logger.info(f"Video title: {video_title}")
        return video_title
    logger.error("Video details not found")
    return None

def get_transcript(video_id):
    """Fetch the transcript of the video."""
    logger.info(f"Fetching transcript for video ID: {video_id}")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = " ".join([entry['text'] for entry in transcript])
        logger.info(f"Transcript fetched successfully. Length: {len(full_transcript)} characters")
        return full_transcript
    except Exception as e:
        logger.error(f"An error occurred while fetching the transcript: {str(e)}")
        return None

def claude_api_request(prompt):
    """Send a request to the Claude Opus API."""
    logger.info("Sending request to Claude Opus API")
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': CLAUDE_API_KEY,
        'anthropic-version': '2023-06-01'
    }
    data = {
        'model': 'claude-3-opus-20240229',
        'max_tokens': 1000,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    response = requests.post(CLAUDE_API_URL, headers=headers, json=data)
    logger.info(f"Claude API response status code: {response.status_code}")
    if response.status_code == 200:
        content = response.json()['content'][0]['text']
        logger.info(f"Claude Opus API response received. Length: {len(content)} characters")
        return content
    else:
        logger.error(f"Error from Claude API: {response.text}")
        return None

def generate_summary(content):
    """Generate a summary of the provided content using Claude Opus API."""
    logger.info("Generating summary")
    prompt = f"""Please provide a comprehensive summary of the following YouTube video transcript. The summary should:

1. Capture the main topics and key points discussed in the video.
2. Highlight any important insights, data, or arguments presented.
3. Maintain the original tone and perspective of the speaker.
4. Be structured in a clear and coherent manner.
5. Be detailed enough to give a thorough understanding of the video content, but concise enough to be quickly digestible.

Here's the transcript:

{content}

Summary:"""
    
    summary = claude_api_request(prompt)
    if summary:
        logger.info("Summary generated successfully")
    else:
        logger.error("Failed to generate summary")
    return summary

def save_to_file(video_id, video_title, summary, transcript):
    """Save the summary and transcript to a file."""
    filename = f"{video_id}_summary.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Video Title: {video_title}\n")
        f.write(f"Video URL: https://www.youtube.com/watch?v={video_id}\n\n")
        f.write("Summary:\n")
        f.write(summary)
        f.write("\n\nFull Transcript:\n")
        f.write(transcript)
    logger.info(f"Summary and transcript saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description="YouTube Video Summarizer with Claude Opus")
    parser.add_argument("url", help="Full URL of the YouTube video to summarize")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        logger.error("Invalid YouTube URL. Please provide a valid YouTube video URL.")
        return

    with tqdm(total=4, desc="Processing", unit="step") as pbar:
        video_title = get_video_details(video_id)
        pbar.update(1)
        
        if video_title:
            transcript = get_transcript(video_id)
            pbar.update(1)
            
            if transcript:
                summary = generate_summary(transcript)
                pbar.update(1)
                
                if summary:
                    save_to_file(video_id, video_title, summary, transcript)
                    pbar.update(1)
                else:
                    logger.error("Failed to generate summary")
            else:
                logger.error("Failed to get transcript")
        else:
            logger.error("Failed to get video details")

    logger.info("Finished processing video")

if __name__ == "__main__":
    main()
