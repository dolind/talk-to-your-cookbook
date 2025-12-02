import pytest
from conftest import get_test_file

from app.services.text_or_image_simple import TextOrImageSimple

TEST_IMAGES = {
    "img_1.png": False,
    "text_0.png": True,
    "img_2.png": False,
    "text_1.png": True,
}


@pytest.mark.parametrize("filename, expected", TEST_IMAGES.items())
def test_looks_text_heavy_with_real_images(filename, expected):
    image_path = get_test_file("storage/pages/" + filename)
    classifier = TextOrImageSimple()
    result = classifier.is_text_page(image_path)
    if not expected:
        result = classifier.is_text_page(image_path)
    assert result == expected, f"Image {filename} misclassified: {result}"
