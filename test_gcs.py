from gcs_storage import get_gcs_storage

print("Testing GCS upload...")
try:
    gcs = get_gcs_storage()
    if not gcs.bucket:
        print("ERROR: Could not initialize GCS bucket.")
        exit(1)

    content = b"This is a test file for GCS upload verification."
    filename = "test_upload_verify.txt"

    print(f"Uploading {filename} to bucket {gcs.bucket_name}...")
    url = gcs.upload_image(content, filename, "text/plain")

    print("Upload successful!")
    print(f"Public URL: {url}")

except Exception as e:
    print(f"ERROR: Upload failed: {e}")
    import traceback

    traceback.print_exc()
