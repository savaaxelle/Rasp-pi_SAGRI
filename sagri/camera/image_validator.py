class JpegImageValidator:
    """Checks that received bytes look like a JPEG image."""

    # JPEG files always start with FF D8.
    JPEG_MAGIC = b"\xff\xd8"

    @classmethod
    def is_valid(cls, image_data: bytes) -> bool:
        return bool(image_data) and image_data.startswith(cls.JPEG_MAGIC)
