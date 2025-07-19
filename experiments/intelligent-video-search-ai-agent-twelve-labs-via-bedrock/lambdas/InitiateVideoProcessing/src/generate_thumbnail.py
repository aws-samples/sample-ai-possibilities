import boto3
import os
import json
import logging
from typing import Dict, Any, Optional
import tempfile
from urllib.parse import urlparse
from ffmpeg_utils import run_ffmpeg_command, get_ffmpeg_path

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ThumbnailGenerator:
    """Generate thumbnails for videos using AWS Lambda with ffmpeg layer"""
    
    def __init__(self, s3_bucket: str):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
        
    def generate_thumbnail_from_s3(self, s3_key: str, video_id: str, 
                                   timestamp: float = 10.0) -> Optional[str]:
        """
        Generate thumbnail from S3 video and upload it back to S3
        
        Args:
            s3_key: S3 key of the video
            video_id: Unique video ID
            timestamp: Timestamp in seconds to capture thumbnail (default: 10s)
            
        Returns:
            Public URL of the thumbnail or None if failed
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download video to temp location
                video_path = os.path.join(temp_dir, "video.mp4")
                thumbnail_path = os.path.join(temp_dir, f"{video_id}_thumb.jpg")
                
                logger.info(f"Downloading video from S3: {s3_key}")
                self.s3_client.download_file(self.s3_bucket, s3_key, video_path)
                
                # Generate thumbnail using ffmpeg
                # Try the specified timestamp first, fall back to 1 second if it fails
                for ts in [timestamp, 1.0]:
                    cmd_args = [
                        '-ss', str(ts),     # Seek to timestamp
                        '-i', video_path,   # Input file
                        '-vframes', '1',    # Extract 1 frame
                        '-q:v', '2',        # Quality level 2
                        '-vf', 'scale=640:-1',  # Scale to 640px width
                        '-y',               # Overwrite output
                        thumbnail_path
                    ]
                    
                    try:
                        result = run_ffmpeg_command(cmd_args, timeout=30)
                        
                        if result.returncode == 0 and os.path.exists(thumbnail_path):
                            logger.info(f"Generated thumbnail at {ts} seconds")
                            break
                        else:
                            logger.warning(f"Failed at {ts}s: {result.stderr}")
                            
                    except Exception as e:
                        logger.error(f"Thumbnail generation failed at {ts}s: {e}")
                        continue
                
                if not os.path.exists(thumbnail_path):
                    logger.error("Failed to generate thumbnail at any timestamp")
                    return None
                
                # Upload thumbnail to S3
                thumbnail_s3_key = f"thumbnails/{video_id}_thumb.jpg"
                
                # Upload with appropriate headers for public access
                self.s3_client.upload_file(
                    thumbnail_path,
                    self.s3_bucket,
                    thumbnail_s3_key,
                    ExtraArgs={
                        'ContentType': 'image/jpeg',
                        'CacheControl': 'max-age=86400'  # Cache for 1 day
                    }
                )
                
                # Return S3 key instead of URL for security
                logger.info(f"Uploaded thumbnail to: s3://{self.s3_bucket}/{thumbnail_s3_key}")
                return thumbnail_s3_key
                
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return None
    
    def generate_from_presigned_url(self, video_url: str, video_id: str,
                                   s3_key: str, timestamp: float = 10.0) -> Optional[str]:
        """
        Alternative method using presigned URL (if direct S3 download fails)
        
        Args:
            video_url: Presigned URL of the video
            video_id: Unique video ID
            s3_key: Original S3 key (for fallback)
            timestamp: Timestamp in seconds to capture thumbnail
            
        Returns:
            Public URL of the thumbnail or None if failed
        """
        try:
            # First try direct S3 download (more efficient)
            return self.generate_thumbnail_from_s3(s3_key, video_id, timestamp)
        except Exception as e:
            logger.warning(f"Direct S3 download failed, trying presigned URL: {e}")
            
            # Fallback to using presigned URL with ffmpeg
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    thumbnail_path = os.path.join(temp_dir, f"{video_id}_thumb.jpg")
                    
                    # Generate thumbnail directly from URL
                    cmd_args = [
                        '-ss', str(timestamp),
                        '-i', video_url,  # Use presigned URL directly
                        '-vframes', '1',
                        '-q:v', '2',
                        '-vf', 'scale=640:-1',
                        '-y',
                        thumbnail_path
                    ]
                    
                    result = run_ffmpeg_command(cmd_args, timeout=30)
                    
                    if result.returncode != 0 or not os.path.exists(thumbnail_path):
                        logger.error(f"Failed to generate thumbnail from URL: {result.stderr}")
                        return None
                    
                    # Upload to S3
                    thumbnail_s3_key = f"thumbnails/{video_id}_thumb.jpg"
                    self.s3_client.upload_file(
                        thumbnail_path,
                        self.s3_bucket,
                        thumbnail_s3_key,
                        ExtraArgs={
                            'ContentType': 'image/jpeg',
                            'CacheControl': 'max-age=86400'
                        }
                    )
                    
                    return thumbnail_s3_key
                    
            except Exception as e:
                logger.error(f"Error generating thumbnail from URL: {str(e)}")
                return None