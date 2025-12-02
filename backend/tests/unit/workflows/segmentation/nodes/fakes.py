from app.schemas.ocr import PageScanUpdate


class FakeSegmentationService:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    async def segment(self, ocr_json, enable_segmentation=False):
        self.calls.append((ocr_json, enable_segmentation))
        if self.exc:
            raise self.exc
        return self.result


class FakeRepo:
    def __init__(self, update_exc=None):
        self.update_calls = []
        self.update_exc = update_exc

    async def update(self, dto: PageScanUpdate):
        self.update_calls.append(dto)
        if self.update_exc:
            raise self.update_exc
        return dto


class FakeBroadcast:
    def __init__(self):
        self.calls = []

    async def __call__(self, msg):
        self.calls.append(msg)
