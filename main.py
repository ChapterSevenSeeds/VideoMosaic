import os
import subprocess
import json
from math import ceil, sqrt
from sys import argv

width = 182
height = 134

def find_video_files(directory):
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv', '.webm', '.v')):
                video_files.append(os.path.join(root, file))
    return sorted(video_files)

def create_video_grid_with_audio(video_files, output_file, offsets=None, gains=None, global_offset=0):
    if len(video_files) == 0:
        print("No video files found.")
        return
    
    if offsets is None:
        offsets = {}
    if gains is None:
        gains = {}
    
    # Calculate grid size (rows and columns) based on the number of videos
    num_videos = len(video_files)
    grid_size = ceil(sqrt(num_videos))
    
    # Shortened filter parameters to reduce command length
    scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    
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
        
        # Check if this video has a specific gain setting
        specific_gain_db = None
        for path_key in gains:
            # Check both absolute and relative paths
            if os.path.basename(video_file) == os.path.basename(path_key):
                specific_gain_db = gains[path_key]
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
            filter_complex += f"[{i}:v]tpad=start_duration={offset_seconds}:start_mode=add:color=black,fifo,setpts=PTS-STARTPTS,{scale_filter}[v{i}];"
            
            # Apply gain and delay to audio
            if specific_gain_db is not None and specific_gain_db != 0:
                filter_complex += f"[{i}:a]volume={specific_gain_db}dB,adelay={final_offset_ms}[a{i}];"
            else:
                filter_complex += f"[{i}:a]adelay={final_offset_ms}|{final_offset_ms}[a{i}];"
        else:
            # No offset, use normal scaling
            filter_complex += f"[{i}:v]{scale_filter}[v{i}];"
            
            # Apply gain to audio if specified
            if specific_gain_db is not None and specific_gain_db != 0:
                filter_complex += f"[{i}:a]volume={specific_gain_db}dB[a{i}];"
            else:
                filter_complex += f"[{i}:a]acopy[a{i}];"
    
    # Create layout configuration for xstack
    layout = "|".join(f"{(i % grid_size) * width}_{(i // grid_size) * height}" for i in range(num_videos))
    
    # Build the video filter complex command with consistent framerate
    v_inputs = ''.join(f'[v{i}]' for i in range(num_videos))
    filter_complex += f"{v_inputs}xstack=inputs={num_videos}:layout={layout},fps=25[xstack];"
    
    # Build the audio filter complex command to mix the audio streams
    a_inputs = ''.join(f'[a{i}]' for i in range(num_videos))
    audio_filter_complex = f"{a_inputs}amix=inputs={num_videos}:normalize=0[mixed_audio]"
    
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

def load_video_settings(json_file_path):
    """Load video offsets and gain settings from a JSON file."""
    if not json_file_path or not os.path.exists(json_file_path):
        return {}, {}
    
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Handle legacy format (direct offsets) or new format (with offsets and gain keys)
        if 'offsets' in data or 'gain' in data:
            # New format with separate offsets and gain sections
            offsets = data.get('offsets', {})
            gains = data.get('gain', {})
        else:
            # Legacy format - assume all keys are offsets
            offsets = data
            gains = {}
        
        # Validate offset values are numbers (milliseconds)
        for path, offset in offsets.items():
            if not isinstance(offset, (int, float)):
                print(f"Warning: Invalid offset value for {path}. Expected number, got {type(offset).__name__}")
                offsets[path] = 0
        
        # Validate gain values are numbers (dB)
        for path, gain in gains.items():
            if not isinstance(gain, (int, float)):
                print(f"Warning: Invalid gain value for {path}. Expected number, got {type(gain).__name__}")
                gains[path] = 0
        
        return offsets, gains
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {json_file_path}: {e}")
        return {}, {}
    except Exception as e:
        print(f"Error loading JSON file {json_file_path}: {e}")
        return {}, {}

if __name__ == "__main__":
    if len(argv) < 3:
        print("Usage: python main.py <directory> <output_file> [json_settings_file]")
        print("\nJSON file format:")
        print('{')
        print('  "offsets": {')
        print('    "video1.mp4": 1000,')
        print('    "video2.mp4": -500')
        print('  },')
        print('  "gain": {')
        print('    "video1.mp4": -3.0,')
        print('    "video2.mp4": 2.5')
        print('  }')
        print('}')
        print("\nNote: offsets in milliseconds, gain in dB")
        exit(1)
    
    # Directory where the subdirectories with videos are located
    directory = argv[1]
    
    # Output video file
    output_file = argv[2]
    
    # Optional JSON file with video settings (offsets and gain)
    json_offsets_file = argv[3] if len(argv) > 3 else None
    
    # Load video settings if JSON file is provided
    video_offsets, video_gains = load_video_settings(json_offsets_file)
    if json_offsets_file and (video_offsets or video_gains):
        print(f"Loaded {len(video_offsets)} video offset(s) and {len(video_gains)} gain setting(s) from {json_offsets_file}")
    
    # Calculate global offset from the most negative offset
    global_offset = calculate_global_offset(video_offsets)
    
    # Find all video files in the directory and its subdirectories
    video_files = find_video_files(directory)
    
    # Create the grid video with mixed audio
    create_video_grid_with_audio(video_files, output_file, video_offsets, video_gains, global_offset)
