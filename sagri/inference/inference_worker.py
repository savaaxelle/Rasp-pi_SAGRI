import time
from pathlib import Path

from sagri.config import ProjectConfig
from sagri.inference.image_preprocessor import ImagePreprocessor
from sagri.inference.label_set import LabelSet
from sagri.inference.model_loader import MobileNetModelLoader
from sagri.inference.prediction_decoder import PredictionDecoder
from sagri.storage.ai_result_repository import AIResultRepository
from sagri.storage.camera_repository import CameraImageRepository

DEFAULT_POLL_INTERVAL = 2
DEFAULT_PREPROCESS_MODE = "mobilenet"


class InferenceWorker:
    """
    Polls new ESP32-CAM images, runs MobileNet inference, stores results.

    Orchestrator only: model loading, preprocessing, and decoding are
    each handled by an injected collaborator.
    """

    def __init__(
        self,
        config: ProjectConfig,
        camera_repository: CameraImageRepository,
        ai_repository: AIResultRepository,
        model_loader: MobileNetModelLoader,
        label_set: LabelSet,
        preprocess_mode: str = DEFAULT_PREPROCESS_MODE,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ):
        self._config = config
        self._camera_repository = camera_repository
        self._ai_repository = ai_repository
        self._model_loader = model_loader
        self._label_set = label_set
        self._preprocess_mode = preprocess_mode
        self._poll_interval = poll_interval

        self._preprocessor = None
        self._decoder = None
        self._processed_images = set()

    def run(self) -> None:
        self._config.ensure_directories()

        print("=" * 55)
        print("MOBILENET IMAGE INFERENCE WORKER")
        print("=" * 55)
        print(f"Camera metadata : {self._config.camera_metadata_file}")
        print(f"Model path      : {self._model_loader.model_path}")
        print(f"AI result       : {self._config.ai_results_file}")
        print(f"Preprocess mode : {self._preprocess_mode}")
        print()

        self._model_loader.wait_until_available()
        self._label_set.load()

        self._preprocessor = ImagePreprocessor(
            self._model_loader.input_width,
            self._model_loader.input_height,
            self._preprocess_mode,
        )
        self._decoder = PredictionDecoder(self._label_set)

        self._processed_images = self._ai_repository.load_processed_image_paths()

        print(f"[INFO] Previously processed: {len(self._processed_images)}")
        print("[WAIT] Waiting for ESP32-CAM images...")
        print()

        try:
            while True:
                self.process_new_images()
                time.sleep(self._poll_interval)
        except KeyboardInterrupt:
            print()
            print("[STOP] Inference worker stopped by user.")

    def process_new_images(self) -> None:
        """Check camera metadata and process every image not yet inferred."""

        for metadata in self._camera_repository.read_all_metadata():
            image_path = metadata.get("image_path")

            if not image_path or image_path in self._processed_images:
                continue

            try:
                self._process_image(metadata)
            except Exception as error:
                print(f"[INFERENCE ERROR] {error}")
                print()

    def _process_image(self, metadata: dict) -> None:
        image_path_text = metadata.get("image_path")

        if not image_path_text or image_path_text in self._processed_images:
            return

        image_path = Path(image_path_text)

        if not image_path.exists():
            print("[WARNING] Image file not found:")
            print(f"          {image_path}")
            return

        print("[IMAGE] Processing:")
        print(f"        {image_path.name}")

        prediction = self._predict_image(image_path)

        result = {
            "camera_id": metadata.get("camera_id"),
            # Currently uses Raspberry Pi receive time. Later this can be
            # replaced with the actual ESP32-CAM capture timestamp.
            "captured_at": metadata.get("raspi_received_time"),
            "image_path": str(image_path),
            "label": prediction["label"],
            "confidence_score": prediction["confidence_score"],
            "class_index": prediction["class_index"],
            "model_version": self._model_loader.model_version,
        }

        self._ai_repository.save(result)
        self._processed_images.add(image_path_text)

        print(f"[AI] Label      : {prediction['label']}")
        print(f"[AI] Confidence : {prediction['confidence_score']:.4f}")
        print(f"[SAVED] {self._config.ai_results_file}")
        print()

    def _predict_image(self, image_path: Path) -> dict:
        input_tensor = self._preprocessor.process(image_path)

        prediction = self._model_loader.model.predict(input_tensor, verbose=0)

        # Some Keras models can have multiple outputs.
        if isinstance(prediction, (list, tuple)):
            prediction = prediction[0]

        class_index, label, confidence = self._decoder.decode(prediction)

        return {
            "class_index": class_index,
            "label": label,
            "confidence_score": round(confidence, 6),
        }
