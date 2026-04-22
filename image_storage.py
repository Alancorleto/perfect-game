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
    # Upload from file
    response = imagekit.files.upload(
        file=file,
        file_name=file_name,
        folder=f"perfect_game/{folder}",
    )
    return response.url
