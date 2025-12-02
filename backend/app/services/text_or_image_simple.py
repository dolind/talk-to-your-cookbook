from app.ports.ocr import TextOrImageService


class TextOrImageSimple(TextOrImageService):
    def __init__(self):
        # we store the number of pages analyzed and make every second an image
        self.counter = 0

    def is_text_page(self, filename):
        self.counter += 1
        return self.counter % 2 == 1
