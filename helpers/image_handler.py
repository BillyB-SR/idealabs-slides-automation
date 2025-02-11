"""
Handles image generation and storage using Google Imagen and Google Cloud Storage
"""

from google import genai
from google.genai import types
from google.cloud import storage
from PIL import Image
from io import BytesIO
import uuid

class ImageHandler:
    def __init__(self, genai_api_key, bucket_name, project_id):
        """
        Initialize with necessary credentials and configuration
        
        Args:
            genai_api_key (str): API key for Google's Generative AI
            bucket_name (str): GCS bucket name for storing images
            project_id (str): Google Cloud project ID
        """
        self.client = genai.Client(api_key=genai_api_key)
        self.storage_client = storage.Client(project=project_id)
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
    
    def generate_and_store_image(self, prompt, aspect_ratio="1:1"):
        """
        Generates an image from a prompt and stores it in GCS
        
        Args:
            prompt (str): Description for image generation
            aspect_ratio (str): One of "1:1", "3:4", "4:3", "9:16", "16:9"
            
        Returns:
            str: Public URL of the stored image
        
        Raises:
            ValueError: If invalid aspect_ratio is provided
        """
        VALID_RATIOS = {"1:1", "3:4", "4:3", "9:16", "16:9"}
        if aspect_ratio not in VALID_RATIOS:
            raise ValueError(f"Invalid aspect_ratio. Must be one of: {VALID_RATIOS}")
        try:
            # Generate image using Imagen
            response = self.client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio
                )
            )
            
            if not response.generated_images:
                raise Exception("No images were generated")
            
            # Get image bytes from response
            image_bytes = response.generated_images[0].image.image_bytes
            
            # Generate unique filename
            filename = f"slides/{uuid.uuid4()}.png"
            
            # Upload to GCS
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                image_bytes,
                content_type='image/png'
            )
            
            # Make the blob publicly accessible and get its public URL
            blob.cache_control = 'public, max-age=31536000'  # Cache for 1 year
            blob.patch()
            
            # Instead of using IAM, use signed URLs with a long expiration
            return f"https://storage.googleapis.com/{self.bucket_name}/{filename}"
            
        except Exception as e:
            print(f"Error in generate_and_store_image: {str(e)}")
            return None
    
    def delete_image(self, image_url):
        """
        Deletes an image from GCS
        
        Args:
            image_url (str): Public URL of the image to delete
        """
        try:
            # Extract filename from URL
            filename = image_url.split('/')[-1]
            blob = self.bucket.blob(f"slides/{filename}")
            blob.delete()
        except Exception as e:
            print(f"Error deleting image: {str(e)}")