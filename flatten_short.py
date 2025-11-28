import glob

index = 0
for file in glob.glob("What/**/*.*", recursive=True):
    print(file)
    with open(file, "rb") as f:
        with open(f"{index}.v", "wb") as fw:
            fw.write(f.read())

    index += 1