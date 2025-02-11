"""
Main automation script that orchestrates the slide updates
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from helpers.slide_updater import PresentationUpdater
from helpers.image_handler import ImageHandler
import config

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
    
    # Initialize updater
    updater = PresentationUpdater(slides_service, image_handler)
    
    # Process the presentation in phases
    try:
        # Phase 1: Create and populate new slides
        new_slide_ids = updater.create_new_slides(
            config.TEMPLATE_PRESENTATION_ID,
            presentation_data['slides']
        )
        print(f"Created {len(new_slide_ids)} new slides")
        
        # Phase 2: Update existing slides text
        updated_text_count = updater.update_existing_slides(
            config.TEMPLATE_PRESENTATION_ID,
            presentation_data['slides']
        )
        print(f"Updated {updated_text_count} existing text elements")
        
        # Phase 3: Update images
        updated_image_count = updater.update_slide_images(
            config.TEMPLATE_PRESENTATION_ID,
            presentation_data['slides']
        )
        print(f"Updated {updated_image_count} images")
        
    except Exception as e:
        print(f"Error updating presentation: {str(e)}")
        raise

if __name__ == "__main__":
    main()