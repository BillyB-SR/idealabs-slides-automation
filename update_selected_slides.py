"""
Script to update images and text for specific slides in a presentation
example usage:
python update_selected_slides.py 1 3 5 7
"""

import json
import argparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from helpers.image_handler import ImageHandler
import config

def update_selected_slides(presentation_id, slides_data, slide_numbers, slides_service, image_handler):
    """
    Updates images and text only for specified slide numbers.
    
    Args:
        presentation_id (str): The ID of the presentation
        slides_data (list): Full slides data from JSON
        slide_numbers (list): List of slide numbers to update
        slides_service: Google Slides service instance
        image_handler: ImageHandler instance
    
    Returns:
        dict: Summary of updates made
    """
    results = {
        'text': {'updated': 0, 'skipped': 0},
        'images': {'updated': 0, 'skipped': 0}
    }
    
    # Convert slide numbers to set for faster lookup
    slide_numbers = set(slide_numbers)
    
    print(f"\nUpdating slides: {sorted(slide_numbers)}")
    
    for slide in slides_data:
        slide_num = slide.get('slideNumber')
        if slide_num not in slide_numbers:
            continue
            
        print(f"\nProcessing Slide {slide_num}...")
        
        if not slide.get('exists'):
            print(f"  Skipping: Slide {slide_num} doesn't exist")
            continue
            
        # Update text elements
        for text_elem in slide.get('elements', {}).get('TEXT', []):
            if text_elem.get('objectId'):
                try:
                    # Delete existing text
                    delete_request = {
                        'deleteText': {
                            'objectId': text_elem['objectId'],
                            'textRange': {'type': 'ALL'}
                        }
                    }
                    
                    # Insert new text
                    insert_request = {
                        'insertText': {
                            'objectId': text_elem['objectId'],
                            'insertionIndex': 0,
                            'text': text_elem['text']
                        }
                    }
                    
                    # Execute both requests together
                    slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': [delete_request, insert_request]}
                    ).execute()
                    
                    results['text']['updated'] += 1
                    print(f"  ✓ Updated text element {text_elem['objectId']}")
                    
                except Exception as e:
                    results['text']['skipped'] += 1
                    print(f"  ✗ Failed to update text {text_elem['objectId']}: {str(e)}")
        
        # Update image elements
        for image_elem in slide.get('elements', {}).get('IMAGE', []):
            if not image_elem.get('objectId'):
                results['images']['skipped'] += 1
                print(f"  Skipping image: No objectId")
                continue
                
            if not image_elem.get('image_prompt'):
                results['images']['skipped'] += 1
                print(f"  Skipping image {image_elem['objectId']}: No image description")
                continue
                
            try:
                # Generate new image
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
                    
                    results['images']['updated'] += 1
                    print(f"  ✓ Updated image {image_elem['objectId']}")
                else:
                    results['images']['skipped'] += 1
                    print(f"  ✗ Failed to generate image for {image_elem['objectId']}")
                    
            except Exception as e:
                results['images']['skipped'] += 1
                print(f"  ✗ Error updating image {image_elem['objectId']}: {str(e)}")
    
    # Print summary
    print("\nUpdate Summary:")
    print(f"Text elements:  {results['text']['updated']} updated, {results['text']['skipped']} skipped")
    print(f"Image elements: {results['images']['updated']} updated, {results['images']['skipped']} skipped")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Update specific slides in presentation')
    parser.add_argument('slides', nargs='+', type=int, 
                      help='Slide numbers to update (e.g., 5 6 7)')
    parser.add_argument('--json-file', default=config.INPUT_FILE,
                      help='Input JSON file (default: config.INPUT_FILE)')
    args = parser.parse_args()
    
    # Read the JSON
    with open(args.json_file, "r") as f:
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
        update_selected_slides(
            config.TEMPLATE_PRESENTATION_ID,
            presentation_data['slides'],
            args.slides,
            slides_service,
            image_handler
        )
        
    except Exception as e:
        print(f"\nError updating presentation: {str(e)}")
        raise

if __name__ == "__main__":
    main()