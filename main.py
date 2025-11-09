import os
import subprocess
import json
from math import ceil, sqrt
from sys import argv

width = 320
height = 180

def find_video_files(directory):
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm', '.v')):
                video_files.append(os.path.join(root, file))
    return sorted(video_files)

def create_video_grid_with_audio(video_files, output_file, offsets=None, global_offset=0):
    if len(video_files) == 0:
        print("No video files found.")
        return
    
    if offsets is None:
        offsets = {}
    
    # Calculate grid size (rows and columns) based on the number of videos
    num_videos = len(video_files)
    grid_size = ceil(sqrt(num_videos))
    
    # Prepare the ffmpeg filter for tiling the videos and mixing the audio
    filter_complex = ""
    for i in range(num_videos):
        video_file = video_files[i]
        
        # Check if this video has a specific offset
        specific_offset_ms = None
        for path_key in offsets:
            # Check both absolute and relative paths
            if os.path.basename(video_file) == os.path.basename(path_key):
                specific_offset_ms = offsets[path_key]
                break
        
        # Calculate final offset: global offset + specific offset (if any)
        if global_offset != 0:
            # Apply global offset to all videos
            final_offset_ms = global_offset + (specific_offset_ms if specific_offset_ms is not None else 0)
        else:
            # No global offset, only apply specific offsets
            final_offset_ms = specific_offset_ms
        
        if final_offset_ms is not None and final_offset_ms != 0:
            # Apply offset using setpts filter for video and audio
            offset_seconds = final_offset_ms / 1000.0
            # Add black video padding for delayed videos to avoid empty slots
            filter_complex += f"[{i}:v]setpts=PTS+{offset_seconds}/TB,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v{i}]; "
            filter_complex += f"[{i}:a]adelay={final_offset_ms}|{final_offset_ms}[a{i}]; "
        else:
            # No offset, use normal scaling
            filter_complex += f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v{i}]; "
            filter_complex += f"[{i}:a]acopy[a{i}]; "
    
    # Create layout configuration for xstack
    layout = ""
    for i in range(num_videos):
        row = i // grid_size
        col = i % grid_size
        layout += f"{col * width}_{row * height}|"
    
    layout = layout.rstrip("|")
    
    # Build the video filter complex command with consistent framerate
    filter_complex += f"{''.join(f'[v{i}]' for i in range(num_videos))}xstack=inputs={num_videos}:layout={layout}[xstack_temp]; "
    filter_complex += f"[xstack_temp]fps=25[xstack]; "  # Force consistent 25fps output
    
    # Build the audio filter complex command to mix the audio streams
    audio_filter_complex = f"{''.join(f'[a{i}]' for i in range(num_videos))}amix=inputs={num_videos}:normalize=0[mixed_audio]"
    
    # Final filter complex string
    filter_complex += audio_filter_complex
    
    # Build ffmpeg command
    command = [
        'ffmpeg',
        '-y'  # Overwrite output file if exists
    ]
    
    # Add all input files
    for video in video_files:
        command.extend(['-i', video.lstrip(".\\")])
    
    # Add the filter complex command
    command.extend([
        '-filter_complex', filter_complex,
        '-map', '[xstack]',  # Map the video grid
        '-map', '[mixed_audio]',  # Map the mixed audio
        '-c:v', 'h264',  # Use H.264 codec for output
        '-preset', 'fast',
        '-crf', '18',  # Better quality parameter for compatibility (was 10, which is very high quality but can cause issues)
        '-profile:v', 'high',  # H.264 profile for better compatibility
        '-level', '4.1',  # H.264 level for broader compatibility
        '-pix_fmt', 'yuv420p',  # Pixel format for maximum compatibility
        '-movflags', '+faststart',  # Move metadata to beginning for faster web/VLC playback
        '-c:a', 'aac',  # Use AAC codec for audio
        '-b:a', '192k',  # Audio bitrate
        '-ar', '48000',  # Audio sample rate for consistency
        '-avoid_negative_ts', 'make_zero',  # Handle negative timestamps better
        output_file
    ])
    
    # Run the command
    print(" ".join(command))
    try:
        subprocess.run(command, check=True)
        print(f"Output video saved as {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during ffmpeg processing: {e}")

def calculate_global_offset(offsets):
    """Calculate global offset from the most negative offset in the JSON."""
    if not offsets:
        return 0
    
    # Find the minimum (most negative) offset value
    min_offset = min(offsets.values())
    
    # If minimum is negative, return its absolute value as global offset
    # If minimum is zero or positive, no global offset needed
    if min_offset < 0:
        global_offset = abs(min_offset)
        print(f"Global offset calculated: {global_offset}ms (to compensate for most negative offset: {min_offset}ms)")
        return global_offset
    else:
        return 0

def load_video_offsets(json_file_path):
    """Load video offsets from a JSON file."""
    if not json_file_path or not os.path.exists(json_file_path):
        return {}
    
    try:
        with open(json_file_path, 'r') as f:
            offsets = json.load(f)
        
        # Validate that all values are numbers (milliseconds)
        for path, offset in offsets.items():
            if not isinstance(offset, (int, float)):
                print(f"Warning: Invalid offset value for {path}. Expected number, got {type(offset).__name__}")
                offsets[path] = 0
        
        return offsets
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {json_file_path}: {e}")
        return {}
    except Exception as e:
        print(f"Error loading JSON file {json_file_path}: {e}")
        return {}

if __name__ == "__main__":
    if len(argv) < 3:
        print("Usage: python main.py <directory> <output_file> [json_offsets_file]")
        exit(1)
    
    # Directory where the subdirectories with videos are located
    directory = argv[1]
    
    # Output video file
    output_file = argv[2]
    
    # Optional JSON file with video offsets
    json_offsets_file = argv[3] if len(argv) > 3 else None
    
    # Load video offsets if JSON file is provided
    video_offsets = load_video_offsets(json_offsets_file)
    if json_offsets_file and video_offsets:
        print(f"Loaded {len(video_offsets)} video offset(s) from {json_offsets_file}")
    
    # Calculate global offset from the most negative offset
    global_offset = calculate_global_offset(video_offsets)
    
    # Find all video files in the directory and its subdirectories
    video_files = find_video_files(directory)
    
    # Create the grid video with mixed audio
    create_video_grid_with_audio(video_files, output_file, video_offsets, global_offset)
