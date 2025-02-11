"""
Handles all slide creation and update operations
"""

import time
import config

class PresentationUpdater:
    def __init__(self, slides_service, image_handler):
        self.service = slides_service
        self.image_handler = image_handler
        self.requests_per_minute = config.REQUESTS_PER_MINUTE
        self.request_interval = 60.0 / self.requests_per_minute  # Time between requests
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_interval:
            time.sleep(self.request_interval - time_since_last)
        self.last_request_time = time.time()
        
    def create_new_slides(self, presentation_id, slides_data):
        """Creates and populates new slides."""
        new_slide_ids = {}
        
        for slide in slides_data:
            if not slide.get('exists'):
                try:
                    # Create the slide with placeholder mappings
                    create_request = {
                        'createSlide': {
                            'insertionIndex': slide['slideNumber'] - 1,
                            'slideLayoutReference': {
                                'predefinedLayout': slide.get('layout', 'BLANK')
                            },
                            'placeholderIdMappings': [
                                {
                                    'layoutPlaceholder': {'type': 'TITLE'},
                                    'objectId': f'{slide["slideNumber"]}_title'
                                },
                                {
                                    'layoutPlaceholder': {'type': 'BODY'},
                                    'objectId': f'{slide["slideNumber"]}_body'
                                }
                            ]
                        }
                    }
                    
                    response = self.service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': [create_request]}
                    ).execute()
                    
                    new_slide_id = response.get('replies', [{}])[0].get('createSlide', {}).get('objectId')
                    if new_slide_id:
                        new_slide_ids[slide['slideNumber']] = new_slide_id
                        # Add content to new slide
                        self._populate_new_slide(presentation_id, new_slide_id, slide)
                    else:
                        print(f"Failed to get new slide ID for slide {slide['slideNumber']}")
                        
                except Exception as e:
                    print(f"Error creating slide {slide['slideNumber']}: {str(e)}")
        
        return new_slide_ids
    
    def _populate_new_slide(self, presentation_id, slide_id, slide_data):
        """Populates a newly created slide with content."""
        requests = []
        
        try:
            # Handle text elements
            for text_elem in slide_data.get('elements', {}).get('TEXT', []):
                if text_elem.get('placeholder'):
                    # Use the mapped placeholder IDs we created
                    object_id = f'{slide_data["slideNumber"]}_{text_elem["placeholder"].lower()}'
                    requests.append({
                        'insertText': {
                            'objectId': object_id,
                            'insertionIndex': 0,
                            'text': text_elem['text']
                        }
                    })
                else:
                    # Create new text box
                    text_box_id = f'{slide_id}_text_{len(requests)}'
                    requests.append({
                        'createShape': {
                            'objectId': text_box_id,
                            'shapeType': 'TEXT_BOX',
                            'elementProperties': {
                                'pageObjectId': slide_id,
                                'size': {'width': {'magnitude': 300, 'unit': 'PT'},
                                       'height': {'magnitude': 100, 'unit': 'PT'}},
                                'transform': {
                                    'scaleX': 1,
                                    'scaleY': 1,
                                    'translateX': 100,
                                    'translateY': 100,
                                    'unit': 'PT'
                                }
                            }
                        }
                    })
                    requests.append({
                        'insertText': {
                            'objectId': text_box_id,
                            'insertionIndex': 0,
                            'text': text_elem['text']
                        }
                    })
            
            # Handle image elements for new slides
            for image_elem in slide_data.get('elements', {}).get('IMAGE', []):
                if image_elem.get('image_prompt'):
                    image_url = self.image_handler.generate_and_store_image(
                        image_elem['image_prompt'],
                        aspect_ratio=image_elem.get('aspect_ratio', '1:1')
                    )
                    
                    if image_url:
                        image_id = f'{slide_id}_image_{len(requests)}'
                        requests.append({
                            'createImage': {
                                'objectId': image_id,
                                'url': image_url,
                                'elementProperties': {
                                    'pageObjectId': slide_id,
                                    'size': {
                                        'width': {'magnitude': 350, 'unit': 'PT'},
                                        'height': {'magnitude': 350, 'unit': 'PT'}
                                    },
                                    'transform': {
                                        'scaleX': 1,
                                        'scaleY': 1,
                                        'translateX': 100,
                                        'translateY': 100,
                                        'unit': 'PT'
                                    }
                                }
                            }
                        })
            
            if requests:
                self.service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': requests}
                ).execute()
                
        except Exception as e:
            print(f"Error populating slide {slide_id}: {str(e)}")
    
    def update_existing_slides(self, presentation_id, slides_data):
        """Updates content in existing slides."""
        updated_count = 0
        skipped_count = 0
        
        for slide in slides_data:
            if slide.get('exists'):
                for text_elem in slide.get('elements', {}).get('TEXT', []):
                    if text_elem.get('objectId'):
                        try:
                            # Wait for rate limit before making request
                            self._wait_for_rate_limit()
                            
                            # Delete existing text
                            delete_request = {
                                'deleteText': {
                                    'objectId': text_elem['objectId'],
                                    'textRange': {
                                        'type': 'ALL'
                                    }
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
                            self.service.presentations().batchUpdate(
                                presentationId=presentation_id,
                                body={'requests': [delete_request, insert_request]}
                            ).execute()
                            
                            updated_count += 1
                            print(f"Successfully updated text element {text_elem['objectId']} on slide {slide['slideNumber']}")
                            
                        except Exception as e:
                            print(f"Failed to update text element {text_elem['objectId']} on slide {slide['slideNumber']}: {str(e)}")
                            skipped_count += 1
                            continue
    
        print(f"Text update summary: {updated_count} updated, {skipped_count} skipped")
        return updated_count, skipped_count
        
    def update_slide_images(self, presentation_id, slides_data):
        """Updates images in existing slides using their objectIds."""
        updated_count = 0
        skipped_count = 0
        
        for slide in slides_data:
            if not slide.get('exists'):
                continue
                
            for image_elem in slide.get('elements', {}).get('IMAGE', []):
                if not image_elem.get('objectId'):
                    print(f"Skipping image on slide {slide['slideNumber']}: No objectId")
                    skipped_count += 1
                    continue
                    
                if not image_elem.get('image_prompt'):
                    print(f"Skipping image {image_elem['objectId']} on slide {slide['slideNumber']}: No image description")
                    skipped_count += 1
                    continue
                    
                try:
                    # Wait for rate limit
                    self._wait_for_rate_limit()
                    
                    # Generate new image from description
                    image_url = self.image_handler.generate_and_store_image(
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
                        
                        self.service.presentations().batchUpdate(
                            presentationId=presentation_id,
                            body={'requests': [replace_request]}
                        ).execute()
                        
                        updated_count += 1
                        print(f"Successfully updated image {image_elem['objectId']} on slide {slide['slideNumber']}")
                    else:
                        print(f"Failed to generate image for {image_elem['objectId']} on slide {slide['slideNumber']}")
                        skipped_count += 1
                        
                except Exception as e:
                    print(f"Failed to update image {image_elem['objectId']} on slide {slide['slideNumber']}: {str(e)}")
                    skipped_count += 1
                    continue
        
        print(f"Image update summary: {updated_count} updated, {skipped_count} skipped")
        return updated_count, skipped_count