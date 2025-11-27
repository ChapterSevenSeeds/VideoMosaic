#!/usr/bin/env python3
"""
Script to remove file extensions from all files in a specified directory.
Usage: python remove_extensions.py <directory_path>
"""

import os
import sys
import argparse
from pathlib import Path


def remove_extensions(directory_path):
    """Remove extensions from all files in the specified directory."""
    try:
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"Error: Directory '{directory_path}' does not exist.")
            return False
            
        if not directory.is_dir():
            print(f"Error: '{directory_path}' is not a directory.")
            return False
        
        # Get all files in directory (not recursive)
        files = [f for f in directory.iterdir() if f.is_file()]
        
        if not files:
            print(f"No files found in '{directory_path}'")
            return True
        
        renamed_count = 0
        skipped_count = 0
        
        for file_path in files:
            # Skip this script file itself
            if file_path.name == "remove_extensions.py":
                print(f"Skipping script file: {file_path.name}")
                skipped_count += 1
                continue
            
            # Get the filename without extension
            new_name = file_path.stem
            
            # Check if the new name would be empty (for files that are only extensions like .gitignore)
            if not new_name.strip():
                print(f"Skipping file with no base name: {file_path.name}")
                skipped_count += 1
                continue
            
            # Create new file path
            new_file_path = file_path.parent / new_name
            
            # Check if a file with the new name already exists
            if new_file_path.exists():
                print(f"Warning: File '{new_name}' already exists. Skipping {file_path.name}")
                skipped_count += 1
                continue
            
            try:
                # Rename the file
                file_path.rename(new_file_path)
                print(f"Renamed: {file_path.name} -> {new_name}")
                renamed_count += 1
            except OSError as e:
                print(f"Error renaming {file_path.name}: {e}")
                skipped_count += 1
        
        print(f"\nExtension removal complete!")
        print(f"Files renamed: {renamed_count}")
        print(f"Files skipped: {skipped_count}")
        return True
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Remove file extensions from all files in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python remove_extensions.py /path/to/directory
  python remove_extensions.py .
  python remove_extensions.py "C:\\Users\\user\\Documents"
        """
    )
    
    parser.add_argument(
        'directory',
        help='Path to the directory containing files to process'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Convert to absolute path for clarity
    directory_path = os.path.abspath(args.directory)
    
    if args.verbose:
        print(f"Processing directory: {directory_path}")
    
    success = remove_extensions(directory_path)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()