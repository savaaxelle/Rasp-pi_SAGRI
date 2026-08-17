import time
from pathlib import Path


class MobileNetModelLoader:
    """
    Loads a Keras MobileNet model and reads its expected input size.

    Currently supports Keras model files: .keras / .h5
    """

    def __init__(self, model_path: Path):
        self._model_path = model_path

        self.model = None
        self.model_version = None
        self.input_width = None
        self.input_height = None

    @property
    def model_path(self) -> Path:
        return self._model_path

    def exists(self) -> bool:
        return self._model_path.exists()

    def load(self) -> None:
        if not self.exists():
            raise FileNotFoundError(f"Model not found: {self._model_path}")

        try:
            import tensorflow as tf
        except ImportError as error:
            raise RuntimeError("TensorFlow is not installed.") from error

        print("[MODEL] Loading MobileNet model...")
        print(f"        {self._model_path}")

        self.model = tf.keras.models.load_model(self._model_path, compile=False)
        self.model_version = self._model_path.stem

        print("[OK] MobileNet model loaded.")

        self._read_model_input_size()

        print(f"[MODEL] Input size : {self.input_width}x{self.input_height}")

    def wait_until_available(self, poll_seconds: int = 5) -> None:
        """Keep waiting until the supervisor's MobileNet model exists."""

        while self.model is None:
            if not self.exists():
                print("[WAIT] MobileNet model not found.")
                print("[WAIT] Expected model:")
                print(f"       {self._model_path}")
                print()
                time.sleep(poll_seconds)
                continue

            try:
                self.load()
            except Exception as error:
                print(f"[MODEL ERROR] {error}")
                print(f"[RETRY] Trying again in {poll_seconds} seconds...")
                time.sleep(poll_seconds)

    def _read_model_input_size(self) -> None:
        """
        Automatically read image input size from model.

        Example: (None, 224, 224, 3) becomes width=224, height=224
        """

        input_shape = self.model.input_shape

        # Some models can contain multiple inputs.
        if isinstance(input_shape, list):
            input_shape = input_shape[0]

        if len(input_shape) != 4:
            raise ValueError(f"Unsupported model input shape: {input_shape}")

        _batch, height, width, channels = input_shape

        if height is None or width is None:
            raise ValueError("Model input resolution is dynamic.")

        if channels != 3:
            raise ValueError("Model input must contain 3 RGB channels.")

        self.input_height = int(height)
        self.input_width = int(width)
