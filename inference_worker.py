from sagri.config import ProjectConfig
from sagri.inference.inference_worker import InferenceWorker
from sagri.inference.label_set import LabelSet
from sagri.inference.model_loader import MobileNetModelLoader
from sagri.storage.ai_result_repository import AIResultRepository
from sagri.storage.camera_repository import CameraImageRepository


def main() -> None:
    config = ProjectConfig.from_env()

    if not config.inference_enabled:
        print("[INFO] Inference worker is disabled (SAGRI_ENABLE_INFERENCE=0).")
        return

    worker = InferenceWorker(
        config=config,
        camera_repository=CameraImageRepository(config),
        ai_repository=AIResultRepository(config),
        model_loader=MobileNetModelLoader(config.model_path),
        label_set=LabelSet(config.labels_file),
    )

    worker.run()


if __name__ == "__main__":
    main()
