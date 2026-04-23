import os
from fastapi import UploadFile
from imagekitio import ImageKit
from pathlib import Path

imagekit = ImageKit(
    private_key=os.getenv("IMAGEKIT_PRIVATE_KEY")
)

# Store URL endpoint for reuse
URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT")


async def upload_image(file: bytes, file_name: str, folder: str) -> str:
    if os.getenv("ENVIRONMENT") == "production":
        return await upload_image_imagekit(file, file_name, folder)
    else:
        return await upload_image_local(file, file_name, folder)


async def upload_image_local(file: bytes, file_name: str, folder: str) -> str:
    # Create folder if it doesn't exist
    folder_path = Path(f"image_storage_local/{folder}")
    folder_path.mkdir(parents=True, exist_ok=True)

    # Save file locally
    file_path = folder_path / file_name
    with open(file_path, "wb") as f:
        f.write(file)

    local_host = os.getenv("LOCAL_HOST", "http://localhost:8000")
    file_url = f"{local_host}/images/{folder}/{file_name}"

    # Return local file path as URL (for testing)
    return file_url


async def upload_image_imagekit(file: bytes, file_name: str, folder: str) -> str:
    # Upload from file
    response = imagekit.files.upload(
        file=file,
        file_name=file_name,
        folder=f"perfect_game/{folder}",
    )
    return response.url
