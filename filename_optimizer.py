#!/usr/bin/env python3
"""
Script to find the maximum number of characters that can be safely removed 
from the front of all filenames in a directory without causing name collisions.
Usage: python filename_optimizer.py <directory_path>
"""

import os
import sys
import argparse
from pathlib import Path
from collections import Counter


def find_safe_prefix_removal(directory_path, perform_rename=False):
    """Find maximum characters that can be removed from start of filenames without collisions."""
    try:
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"Error: Directory '{directory_path}' does not exist.")
            return None
            
        if not directory.is_dir():
            print(f"Error: '{directory_path}' is not a directory.")
            return None
        
        # Get all files in directory (not recursive)
        files = [f for f in directory.iterdir() if f.is_file()]
        
        if not files:
            print(f"No files found in '{directory_path}'")
            return None
        
        if len(files) == 1:
            filename = files[0].name
            max_removal = len(filename) - 1
            print(f"Only one file found: '{filename}'")
            print(f"Can safely remove up to {max_removal} characters from the front")
            
            if perform_rename and max_removal > 0:
                new_name = filename[max_removal:]
                if new_name.strip():  # Make sure we don't create empty name
                    try:
                        # files[0].rename(files[0].parent / new_name)
                        print(f"Renamed: '{filename}' -> '{new_name}'")
                    except OSError as e:
                        print(f"Error renaming file: {e}")
                else:
                    print("Cannot rename: would result in empty filename")
            
            return max_removal
        
        filenames = [f.name for f in files]
        min_length = min(len(name) for name in filenames)
        
        print(f"Found {len(files)} files")
        print(f"Shortest filename length: {min_length}")
        print(f"Filenames: {filenames[:5]}{'...' if len(filenames) > 5 else ''}")
        
        # Test removing characters from the front
        max_safe_removal = 0
        
        for chars_to_remove in range(1, min_length):
            # Create truncated filenames
            truncated = [name[chars_to_remove:] for name in filenames]
            
            # Check for collisions (duplicates)
            if len(set(truncated)) == len(truncated):
                # No collisions
                max_safe_removal = chars_to_remove
            else:
                # Found collision, stop here
                break
        
        print(f"\nResult:")
        print(f"Maximum safe characters to remove from front: {max_safe_removal}")
        
        if max_safe_removal > 0:
            print(f"\nExample transformations:")
            for i, filename in enumerate(filenames[:3]):
                new_name = filename[max_safe_removal:]
                print(f"  '{filename}' -> '{new_name}'")
                if i >= 2:
                    break
            
            # Show potential character savings
            total_chars_saved = sum(max_safe_removal for _ in filenames)
            print(f"\nTotal characters that would be saved: {total_chars_saved}")
            
            # Perform renaming if requested
            if perform_rename:
                print(f"\nPerforming rename operation...")
                renamed_count = 0
                error_count = 0
                
                for file_path in files:
                    old_name = file_path.name
                    new_name = old_name[max_safe_removal:]
                    
                    # Skip this script file
                    if old_name == "filename_optimizer.py":
                        print(f"Skipping script file: {old_name}")
                        continue
                    
                    if new_name.strip():  # Make sure we don't create empty name
                        try:
                            new_file_path = file_path.parent / new_name
                            file_path.rename(new_file_path)
                            print(f"Renamed: '{old_name}' -> '{new_name}'")
                            renamed_count += 1
                        except OSError as e:
                            print(f"Error renaming '{old_name}': {e}")
                            error_count += 1
                    else:
                        print(f"Skipping '{old_name}': would result in empty filename")
                        error_count += 1
                
                print(f"\nRename operation complete!")
                print(f"Files renamed: {renamed_count}")
                print(f"Files skipped/errors: {error_count}")
        else:
            print("Cannot safely remove any characters without causing collisions.")
            if perform_rename:
                print("No renaming performed.")
        
        return max_safe_removal
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Find maximum characters that can be safely removed from filename prefixes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python filename_optimizer.py /path/to/directory
  python filename_optimizer.py .
  python filename_optimizer.py "C:\\Users\\user\\Videos"
  python filename_optimizer.py . --rename
  python filename_optimizer.py /path/to/videos -r -v
        """
    )
    
    parser.add_argument(
        'directory',
        help='Path to the directory containing files to analyze'
    )
    
    parser.add_argument(
        '-r', '--rename',
        action='store_true',
        help='Actually perform the renaming operation (removes prefix characters)'
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
        print(f"Analyzing directory: {directory_path}")
    
    if args.rename:
        print("RENAME MODE: Files will be renamed!")
        confirm = input("Are you sure you want to proceed? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    result = find_safe_prefix_removal(directory_path, args.rename)
    
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()