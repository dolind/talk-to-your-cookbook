from io import BytesIO

import pytest
from PIL import Image

from app.infra.thumbnail_pillow import PillowThumbnailService


@pytest.mark.asyncio
async def test_generate_thumbnail_default(tmp_path):
    src_file = tmp_path / "source.jpg"
    img = Image.new("RGB", (500, 400), color="blue")
    img.save(src_file, format="JPEG")

    # Generate thumbnail
    service = PillowThumbnailService(size=(300, 300))
    thumb_bytes = await service.generate_thumbnail(str(src_file))

    # Load thumbnail from bytes
    thumb_img = Image.open(BytesIO(thumb_bytes))

    # Ensure JPEG format
    assert thumb_img.format == "JPEG"

    # Ensure the longest edge is 300px
    width, height = thumb_img.size
    assert max(width, height) == 300


@pytest.mark.asyncio
async def test_generate_thumbnail_custom_size_and_format(tmp_path):
    # Create a temporary source image (800x600 px)
    src_file = tmp_path / "source.png"
    img = Image.new("RGBA", (800, 600), color=(255, 0, 0, 128))
    img.save(src_file, format="PNG")

    # Generate thumbnail with custom size and PNG format
    custom_size = (100, 50)
    service = PillowThumbnailService(size=custom_size, fmt="PNG")
    thumb_bytes = await service.generate_thumbnail(str(src_file))

    # Load thumbnail from bytes
    thumb_img = Image.open(BytesIO(thumb_bytes))

    # Ensure PNG format
    assert thumb_img.format == "PNG"

    # Ensure dimensions fit within custom size bounds
    width, height = thumb_img.size
    assert width <= custom_size[0] and height <= custom_size[1]


@pytest.mark.asyncio
async def test_generate_thumbnail_nonexistent_file(tmp_path):
    # Nonexistent source path should raise an IOError when opening
    service = PillowThumbnailService()
    with pytest.raises(FileNotFoundError):  # could be FileNotFoundError or OSError
        await service.generate_thumbnail(str(tmp_path / "no_file.jpg"))
