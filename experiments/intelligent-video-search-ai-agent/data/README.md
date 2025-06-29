# Sample Data
HuggingFace is a valuable source of sample datasets. When downloading datasets, please pay close attention to their licenses and terms of use.

## Dataset Details
Dataset: `HuggingFaceFV/finevideo`

### Source
https://huggingface.co/datasets/HuggingFaceFV/finevideo

### Interactive Explorer
You can preview the dataset contents using the FineVideo Explorer:
https://huggingface.co/spaces/HuggingFaceFV/FineVideo-Explorer

### Download Instructions
The complete dataset is approximately 600GB in size. You can use the provided `download.py` script to download a subset of videos.

#### Authentication Steps
1. Install the Hugging Face CLI: `pip install huggingface_hub`
2. Login via CLI: `huggingface-cli login`
3. Enter your HuggingFace access token when prompted (get token from https://huggingface.co/settings/tokens)

> **Security Note**: The login process creates a `.huggingface` directory in your home folder containing authentication details. Never commit this directory or your access tokens to version control or share them publicly. Add `.huggingface/` to your `.gitignore` file.

#### Requirements & Limitations
1. Dataset access is gated - you must:
   - Visit the source link above
   - Request and receive access approval
   - Login to HuggingFace via CLI before running the download script
2. Ensure you have sufficient storage space for your desired number of video downloads
3. A stable internet connection is recommended due to large file sizes

## License Information
This dataset is licensed under Creative Commons and is not owned by AWS. It is provided solely as an example dataset. You are free to use alternative datasets or your own video content that meets your requirements and usage rights.
```
