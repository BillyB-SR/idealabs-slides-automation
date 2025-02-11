"""
Script to set up Google Cloud Storage bucket for slide images
"""

from google.cloud import storage
import argparse
import config

def setup_storage(bucket_name=None, region=None):
    """
    Creates and configures a GCS bucket for storing generated images.
    """
    # Use config values if not provided
    bucket_name = bucket_name or config.GCS_BUCKET_NAME
    region = region or config.GCS_REGION
    
    # Initialize the client
    storage_client = storage.Client(project=config.PROJECT_ID)
    
    try:
        # Check if bucket exists
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket:
            print(f"Bucket {bucket_name} already exists")
        else:
            # Create new bucket with public read access
            bucket = storage_client.bucket(bucket_name)
            bucket.create(location=region)
            print(f"Created bucket {bucket_name} in {region}")
        
        # Configure bucket
        # Make bucket public
        bucket.make_public(recursive=True, future=True)
        print("Configured bucket for public access")
        
        # Create slides/ prefix (folder)
        blob = bucket.blob(config.IMAGE_PREFIX)
        blob.upload_from_string('')
        # Make sure the folder is public too
        blob.make_public()
        print(f"Created {config.IMAGE_PREFIX} prefix in bucket")
        
        print("\nBucket setup complete!")
        print(f"Base URL for objects: https://storage.googleapis.com/{bucket_name}/")
        
        # Print required permissions
        print("\nRequired IAM roles for service account:")
        print("1. roles/storage.objectViewer")
        print("2. roles/storage.objectCreator")
        print("3. roles/storage.legacyBucketWriter")
        
    except Exception as e:
        print(f"Error setting up bucket: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Set up GCS bucket for slide images')
    parser.add_argument('--bucket', help=f'Name for the GCS bucket (default: {config.GCS_BUCKET_NAME})')
    parser.add_argument('--region', help=f'Region for the bucket (default: {config.GCS_REGION})')
    
    args = parser.parse_args()
    setup_storage(args.bucket, args.region)

if __name__ == "__main__":
    main()