import os
import subprocess
from math import ceil, sqrt

width = 320
height = 240

def find_video_files(directory):
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv')):
                video_files.append(os.path.join(root, file))
    return video_files

def create_video_grid_with_audio(video_files, output_file):
    if len(video_files) == 0:
        print("No video files found.")
        return
    
    # Calculate grid size (rows and columns) based on the number of videos
    num_videos = len(video_files)
    grid_size = ceil(sqrt(num_videos))
    
    # Prepare the ffmpeg filter for tiling the videos and mixing the audio
    filter_complex = ""
    for i in range(num_videos):
        filter_complex += f"[{i}:v]scale={width}:{height}[v{i}]; "  # Rescale each video to 320x240 for uniformity
    
    # Create layout configuration for xstack
    layout = ""
    for i in range(num_videos):
        row = i // grid_size
        col = i % grid_size
        layout += f"{col * width}_{row * height}|"
    
    layout = layout.rstrip("|")
    
    # Build the video filter complex command
    filter_complex += f"{''.join(f'[v{i}]' for i in range(num_videos))}xstack=inputs={num_videos}:layout={layout}[xstack]; "
    
    # Build the audio filter complex command to mix the audio streams
    audio_filter_complex = f"{''.join(f'[{i}:a]' for i in range(num_videos))}amix=inputs={num_videos}[mixed_audio]"
    
    # Final filter complex string
    filter_complex += audio_filter_complex
    
    # Build ffmpeg command
    command = [
        'ffmpeg',
        '-y'  # Overwrite output file if exists
    ]
    
    # Add all input files
    for video in video_files:
        command.extend(['-i', video])
    
    # Add the filter complex command
    command.extend([
        '-filter_complex', filter_complex,
        '-map', '[xstack]',  # Map the video grid
        '-map', '[mixed_audio]',  # Map the mixed audio
        '-c:v', 'h264_nvenc',  # Use H.264 codec for output
        '-preset', 'fast',
        '-crf', '18',  # Quality parameter (lower is better quality)
        '-c:a', 'aac',  # Use AAC codec for audio
        '-b:a', '192k',  # Audio bitrate
        output_file
    ])
    
    # Run the command
    try:
        subprocess.run(command, check=True)
        print(f"Output video saved as {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg processing: {e}")

if __name__ == "__main__":
    # Directory where the subdirectories with videos are located
    directory = r"X:\TV Shows\Psych"
    
    # Output video file
    output_file = "no.mp4"
    
    # Find all video files in the directory and its subdirectories
    video_files = find_video_files(directory)
    
    # Create the grid video with mixed audio
    create_video_grid_with_audio(video_files, output_file)
