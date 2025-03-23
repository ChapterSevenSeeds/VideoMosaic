import glob
import os

index = 341
for file in glob.glob("What/**/*.mkv", recursive=True):
    os.rename(file, f"{index}.v")

    index += 1