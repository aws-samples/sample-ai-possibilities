from datasets import load_dataset
stream = load_dataset("HuggingFaceFV/finevideo", split="train", streaming=True)

for i, sample in enumerate(stream.take(25)):
    fname = sample.get("original_video_filename") or f"video_{i}.mp4"
    with open(fname, "wb") as f:
        f.write(sample["mp4"])
    print("Saved:", fname)
