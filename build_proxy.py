#!/usr/bin/env python3
"""
Video Proxy Generator1
Recursively processes video files to create low-resolution proxy versions
with random 5-second clips and metadata title cards.
"""

import os
import random
import argparse


from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

try:
    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
    from moviepy.video.fx import resize
except ImportError:
    print("Error: MoviePy is required. Install with: pip install moviepy")
    exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Error: tqdm is required for progress bars. Install with: pip install tqdm")
    exit(1)

try:
    from PIL import Image, ExifTags
except ImportError:
    print("Warning: Pillow not found. Date/location extraction will be limited.")
    Image = None
    ExifTags = None

# Configuration constants
SOURCE_DIRECTORY = "/testdata"
OUTPUT_DIRECTORY = "/video_clip_proxies"

# Supported video formats
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}

def get_video_metadata(video_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract date and location metadata from video file.
    Returns (date_str, location_str) tuple.
    """
    date_str = None
    location_str = None
    
    try:
        # Try to get file creation/modification date as fallback
        stat = os.stat(video_path)
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        date_str = mod_time.strftime("%Y-%m-%d %H:%M")
        
        # For more advanced metadata extraction, you might want to use:
        # - exifread for video files with EXIF data
        # - ffprobe (via subprocess) for video metadata
        # - mediainfo-python for comprehensive media information
        
        # Basic filename-based location extraction (if filename contains location info)
        filename = Path(video_path).stem
        # This is a simple example - you might want to implement more sophisticated parsing
        if any(keyword in filename.lower() for keyword in ['paris', 'london', 'tokyo', 'nyc', 'berlin']):
            for city in ['paris', 'london', 'tokyo', 'nyc', 'berlin']:
                if city in filename.lower():
                    location_str = city.title()
                    break
    
    except Exception as e:
        print(f"Warning: Could not extract metadata from {video_path}: {e}")
    
    return date_str, location_str

def create_title_overlay(text: str, duration: float, size: Tuple[int, int] = (640, 360)) -> TextClip:
    """
    Create a text overlay with the given text.
    """
    title_overlay = TextClip(
        text,
        fontsize=20,
        color='white',
        stroke_color='black',
        stroke_width=2,
        method='caption',
        align='left'
    ).set_duration(duration).set_position(('left', 'top')).set_margin(10)
    
    return title_overlay

def process_video_file(input_path: str, output_dir: str, target_width: int = 640, pbar: Optional[tqdm] = None) -> bool:
    """
    Process a single video file to create a proxy version.
    
    Args:
        input_path: Path to input video file
        output_dir: Directory to save proxy version
        target_width: Target width for low-res version
        pbar: Optional progress bar for updates
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if pbar:
            pbar.set_description(f"Processing: {Path(input_path).name}")
        
        # Load video clip
        with VideoFileClip(input_path) as video:
            duration = video.duration
            
            # Skip videos shorter than 5 seconds
            if duration < 5:
                if pbar:
                    pbar.write(f"Skipping {Path(input_path).name}: duration {duration:.1f}s < 5s")
                return False
            
            # Select random 5-second sequence
            max_start_time = duration - 5
            start_time = random.uniform(0, max_start_time)
            end_time = start_time + 5
            
            if pbar:
                pbar.set_description(f"Extracting clip: {Path(input_path).name}")
            
            # Extract 5-second clip
            clip = video.subclip(start_time, end_time)
            
            # Create low-resolution version
            # Calculate target height maintaining aspect ratio
            original_width, original_height = clip.size
            target_height = int((target_width / original_width) * original_height)
            
            # Resize to low resolution
            low_res_clip = resize(clip, width=target_width)
            
            # Extract metadata
            date_str, location_str = get_video_metadata(input_path)
            
            # Create title card text
            title_parts = []
            if date_str:
                title_parts.append(f"Date: {date_str}")
            if location_str:
                title_parts.append(f"Location: {location_str}")
            
            filename = Path(input_path).stem
            title_parts.append(f"File: {filename}")
            
            title_text = "\n".join(title_parts) if title_parts else f"File: {filename}"
            
            # Create title overlay
            title_overlay = create_title_overlay(
                title_text, 
                duration=5.0
            )
            
            # Combine video clip with text overlay
            final_clip = CompositeVideoClip([
                low_res_clip,
                title_overlay
            ], size=(target_width, target_height))
            
            # Keep original 5-second duration
            final_clip = final_clip.set_duration(5.0)
            
            # Generate output filename
            output_filename = f"{filename}_proxy.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            if pbar:
                pbar.set_description(f"Rendering: {Path(input_path).name}")
            
            # Write the final video
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            if pbar:
                pbar.write(f"✓ Successfully created 5s proxy for {filename}")
            return True
            
    except Exception as e:
        if pbar:
            pbar.write(f"✗ Error processing {Path(input_path).name}: {e}")
        else:
            print(f"✗ Error processing {input_path}: {e}")
        return False

def find_video_files(directory: str) -> list:
    """
    Recursively find all video files in directory.
    """
    video_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in VIDEO_EXTENSIONS:
                video_files.append(os.path.join(root, file))
    
    return video_files

def main():
    parser = argparse.ArgumentParser(description='Create proxy versions of video files')
    parser.add_argument('--width', type=int, default=640,
                       help='Target width for proxy videos (default: 640)')
    parser.add_argument('--dry-run', action='store_true',
                       help='List files that would be processed without processing them')
    parser.add_argument('--source-dir', default=SOURCE_DIRECTORY,
                       help=f'Override source directory (default: {SOURCE_DIRECTORY})')
    parser.add_argument('--output-dir', default=OUTPUT_DIRECTORY,
                       help=f'Override output directory (default: {OUTPUT_DIRECTORY})')
    
    args = parser.parse_args()
    
    # Use the configured directories
    input_dir = args.source_dir
    output_dir = args.output_dir
    
    # Validate input directory
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return 1
    
    # Create output directory
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)
    
    # Find all video files
    print(f"Searching for video files in: {input_dir}")
    video_files = find_video_files(input_dir)
    
    if not video_files:
        print("No video files found.")
        return 0
    
    print(f"Found {len(video_files)} video files")
    
    if args.dry_run:
        print("\nFiles that would be processed:")
        for video_file in video_files:
            print(f"  {video_file}")
        return 0
    
    # Process each video file with progress bar
    successful = 0
    failed = 0
    
    with tqdm(total=len(video_files), desc="Processing videos", unit="video") as pbar:
        for video_file in video_files:
            if process_video_file(video_file, output_dir, args.width, pbar):
                successful += 1
            else:
                failed += 1
            pbar.update(1)
    
    print(f"\nProcessing complete:")
    print(f"  ✓ Successful: {successful}")
    print(f"  ✗ Failed: {failed}")
    print(f"  📁 Source directory: {input_dir}")
    print(f"  📁 Output directory: {output_dir}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())