from pathlib import Path

import numpy as np
from PIL import Image

VALID_PREPROCESS_MODES = ("mobilenet", "zero_one", "raw")


class ImagePreprocessor:
    """
    Preprocess one ESP32-CAM image for MobileNet inference.

    JPEG -> RGB -> Resize -> NumPy float32 -> Normalization -> Batch tensor
    """

    def __init__(
        self,
        target_width: int,
        target_height: int,
        preprocess_mode: str = "mobilenet",
    ):
        if preprocess_mode not in VALID_PREPROCESS_MODES:
            raise ValueError(f"Unknown preprocessing mode: {preprocess_mode}")

        self._target_width = target_width
        self._target_height = target_height
        self._preprocess_mode = preprocess_mode

    def process(self, image_path: Path) -> np.ndarray:
        resize_filter = (
            Image.Resampling.BILINEAR
            if hasattr(Image, "Resampling")
            else Image.BILINEAR
        )

        with Image.open(image_path) as image:
            image = image.convert("RGB")

            image = image.resize(
                (self._target_width, self._target_height),
                resize_filter,
            )

            image_array = np.asarray(image, dtype=np.float32)

        if self._preprocess_mode == "mobilenet":
            # 0..255 -> -1..1
            image_array = (image_array / 127.5) - 1.0
        elif self._preprocess_mode == "zero_one":
            # 0..255 -> 0..1
            image_array = image_array / 255.0
        # "raw" leaves the array unchanged.

        return np.expand_dims(image_array, axis=0)
