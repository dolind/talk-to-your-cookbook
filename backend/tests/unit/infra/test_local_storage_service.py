import io
import os
import tempfile

import pytest
from fastapi import UploadFile
from PIL import Image

from app.infra.storage_local import LocalStorageService


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageService(base_path=tmpdir)
        yield storage, tmpdir


@pytest.mark.asyncio
async def test_save_and_load_image(temp_storage):
    storage, tmpdir = temp_storage

    # Create fake image upload
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)

    upload = UploadFile(filename="test.jpg", file=buffer)
    saved_path = await storage.save_image(upload, "test123.jpg")

    assert os.path.exists(saved_path)

    loaded_img = await storage.load_image("test123")
    assert isinstance(loaded_img, Image.Image)
    assert loaded_img.size == (100, 100)


@pytest.mark.asyncio
async def test_delete_image_and_json(temp_storage):
    storage, tmpdir = temp_storage

    # Create fake image and json files
    img_path = os.path.join(storage.recipe_image_dir, "file.jpg")
    json_path = os.path.join(storage.json_dir, "file.jpg")

    with open(img_path, "wb") as f:
        f.write(b"image content")

    with open(json_path, "w") as f:
        f.write("{}")

    assert os.path.exists(img_path)
    assert os.path.exists(json_path)

    await storage.delete("file.jpg")

    assert not os.path.exists(img_path)
    assert not os.path.exists(json_path)


@pytest.mark.asyncio
async def test_save_and_read_json(temp_storage):
    storage, _ = temp_storage
    id = "12"
    data = {"foo": "bar"}
    path = await storage.get_json_path(id)

    await storage.save_json(data, id)
    assert os.path.exists(path)

    read_data = await storage.read_json(id)
    assert read_data == data


@pytest.mark.asyncio
async def test_rename_image(temp_storage):
    storage, _ = temp_storage

    # Create a temp image file
    src_path = os.path.join(storage.recipe_image_dir, "old.jpg")
    with open(src_path, "wb") as f:
        f.write(b"abc")

    new_path = await storage.rename(src_path, "new.jpg")
    assert os.path.exists(new_path)
    assert not os.path.exists(src_path)


@pytest.mark.asyncio
async def test_get_image_path(temp_storage):
    storage, _ = temp_storage
    image_id = "abc123"

    path = await storage.get_image_path(image_id)
    assert path.endswith(os.path.join("images", f"{image_id}.jpg"))
    assert os.path.dirname(path) == storage.recipe_image_dir


@pytest.mark.asyncio
async def test_get_json_path(temp_storage):
    storage, _ = temp_storage
    image_id = "xyz789"

    path = await storage.get_json_path(image_id)
    assert path.endswith(os.path.join("ocr", f"{image_id}.json"))
    assert os.path.dirname(path) == storage.json_dir


# ---------------------------------------------------------------------------
# _get_dir
# ---------------------------------------------------------------------------


def test_get_dir_variants(temp_storage):
    storage, tmpdir = temp_storage

    assert storage._get_dir("recipe") == storage.recipe_image_dir
    assert storage._get_dir("whatever") == storage.recipe_image_dir
    assert storage._get_dir("scanner") == storage.scanner_image_dir


# ---------------------------------------------------------------------------
# save_binary_image
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_binary_image(temp_storage):
    storage, tmpdir = temp_storage

    data = b"123456789"
    fname = "bin.jpg"

    path = await storage.save_binary_image(data, fname)
    assert os.path.exists(path)

    with open(path, "rb") as f:
        assert f.read() == data


@pytest.mark.asyncio
async def test_save_binary_image_scanner(temp_storage):
    storage, tmpdir = temp_storage

    data = b"abc"
    fname = "scan.jpg"

    path = await storage.save_binary_image(data, fname, kind="scanner")
    assert os.path.dirname(path) == storage.scanner_image_dir
    assert os.path.exists(path)


# ---------------------------------------------------------------------------
# save_image(kind="scanner")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_image_scanner(temp_storage):
    storage, tmpdir = temp_storage

    buffer = io.BytesIO(b"fake-img-data")
    upload = UploadFile(filename="x.jpg", file=buffer)

    saved = await storage.save_image(upload, "scan.jpg", kind="scanner")
    assert os.path.dirname(saved) == storage.scanner_image_dir
    assert os.path.exists(saved)


# ---------------------------------------------------------------------------
# load_image(kind="scanner")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_image_scanner(temp_storage):
    storage, tmpdir = temp_storage

    # prepare a real jpg in scanner folder
    img = Image.new("RGB", (64, 64), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    # Write scanner image manually
    path = os.path.join(storage.scanner_image_dir, "abc.jpg")
    with open(path, "wb") as f:
        f.write(buf.read())

    loaded = await storage.load_image("abc", kind="scanner")
    assert isinstance(loaded, Image.Image)
    assert loaded.size == (64, 64)


# ---------------------------------------------------------------------------
# delete(kind="scanner")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_scanner_and_json(temp_storage):
    storage, _ = temp_storage

    scan_file = os.path.join(storage.scanner_image_dir, "file.jpg")
    json_file = os.path.join(storage.json_dir, "file.jpg")

    with open(scan_file, "wb") as f:
        f.write(b"img")
    with open(json_file, "w") as f:
        f.write("{}")

    assert os.path.exists(scan_file)
    assert os.path.exists(json_file)

    await storage.delete("file.jpg", kind="scanner")

    assert not os.path.exists(scan_file)
    assert not os.path.exists(json_file)


# ---------------------------------------------------------------------------
# copy_to_recipe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_copy_to_recipe_success(temp_storage):
    storage, tmpdir = temp_storage

    src = os.path.join(storage.scanner_image_dir, "test.jpg")
    dst = os.path.join(storage.recipe_image_dir, "test.jpg")

    with open(src, "wb") as f:
        f.write(b"copy-me")

    new_path = await storage.copy_to_recipe("test.jpg")

    assert new_path == dst
    assert os.path.exists(dst)

    with open(dst, "rb") as f:
        assert f.read() == b"copy-me"


@pytest.mark.asyncio
async def test_copy_to_recipe_missing_raises(temp_storage):
    storage, _ = temp_storage

    with pytest.raises(FileNotFoundError):
        await storage.copy_to_recipe("does_not_exist.jpg")


# ---------------------------------------------------------------------------
# get_file_path
# ---------------------------------------------------------------------------


def test_get_file_path(temp_storage):
    storage, tmpdir = temp_storage

    rel = "models/u2net.pth"
    abs_path = storage.get_file_path(rel)

    assert abs_path == os.path.join(tmpdir, rel)


# ---------------------------------------------------------------------------
# save_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_file(temp_storage):
    storage, tmpdir = temp_storage

    rel = "models/m1.bin"
    data = b"abcdef"

    abs_path = await storage.save_file(data, rel)
    assert abs_path == os.path.join(tmpdir, rel)
    assert os.path.exists(abs_path)

    with open(abs_path, "rb") as f:
        assert f.read() == data


# ---------------------------------------------------------------------------
# save_json – non-ASCII content (optional behavior verification)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_json_unicode(temp_storage):
    storage, _ = temp_storage
    image_id = "unicode"
    data = {"text": "café 🍰"}

    await storage.save_json(data, image_id)
    path = os.path.join(storage.json_dir, f"{image_id}.json")

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
        assert "café" in raw
        assert "🍰" in raw

    read_back = await storage.read_json(image_id)
    assert read_back == data
