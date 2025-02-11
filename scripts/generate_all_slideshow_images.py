"""
Script to only update images in an existing presentation
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from helpers.image_handler import ImageHandler
import config

def update_presentation_images(presentation_id, slides_data, slides_service, image_handler):
    """Updates only the images in the presentation."""
    updated_count = 0
    skipped_count = 0
    
    print("\nStarting image updates...")
    for slide in slides_data:
        print(f"\nProcessing Slide {slide['slideNumber']}...")
        
        for image_elem in slide.get('elements', {}).get('IMAGE', []):
            if not image_elem.get('objectId'):
                print(f"  Skipping image: No objectId")
                skipped_count += 1
                continue
                
            if not image_elem.get('image_prompt'):
                print(f"  Skipping image {image_elem['objectId']}: No image description")
                skipped_count += 1
                continue
                
            try:
                # Generate new image from description
                print(f"  Generating image for: {image_elem['image_prompt'][:50]}...")
                image_url = image_handler.generate_and_store_image(
                    image_elem['image_prompt'],
                    aspect_ratio=image_elem.get('aspect_ratio', '1:1')
                )
                
                if image_url:
                    # Replace existing image
                    replace_request = {
                        'replaceImage': {
                            'imageObjectId': image_elem['objectId'],
                            'imageReplaceMethod': 'CENTER_CROP',
                            'url': image_url
                        }
                    }
                    
                    slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': [replace_request]}
                    ).execute()
                    
                    updated_count += 1
                    print(f"  ✓ Successfully updated image {image_elem['objectId']}")
                else:
                    print(f"  ✗ Failed to generate image for {image_elem['objectId']}")
                    skipped_count += 1
                    
            except Exception as e:
                print(f"  ✗ Error updating image {image_elem['objectId']}: {str(e)}")
                skipped_count += 1
                continue
    
    print(f"\nImage update summary:")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total processed: {updated_count + skipped_count}")
    
    return updated_count, skipped_count

def main():
    # Read the JSON exported from Google Apps Script
    with open(config.INPUT_FILE, "r") as f:
        presentation_data = json.load(f)
    
    # Initialize services
    credentials = service_account.Credentials.from_service_account_file(
        config.CREDENTIALS_FILE,
        scopes=['https://www.googleapis.com/auth/presentations']
    )
    slides_service = build('slides', 'v1', credentials=credentials)
    
    # Initialize image handler
    image_handler = ImageHandler(
        genai_api_key=config.GENAI_API_KEY,
        bucket_name=config.GCS_BUCKET_NAME,
        project_id=config.PROJECT_ID
    )
    
    try:
        updated_count, skipped_count = update_presentation_images(
            config.TEMPLATE_PRESENTATION_ID,
            presentation_data['slides'],
            slides_service,
            image_handler
        )
        
    except Exception as e:
        print(f"\nError updating presentation: {str(e)}")
        raise

if __name__ == "__main__":
    main()