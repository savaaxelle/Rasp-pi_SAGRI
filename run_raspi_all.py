from sagri.config import DEFAULT_ESP_CAM_BASE_URL, ProjectConfig
from sagri.supervisor.process_supervisor import ProcessSupervisor

# Programs launched as subprocesses, mapped to whether they should be
# restarted automatically if they stop. inference_worker.py and
# cloud_adapter.py are added conditionally (see build_programs()).
BASE_PROGRAMS = {
    "run_sensor_receiver.py": True,
    "esp_cam_scheduler.py": True,
    "local_api.py": True,
}


def build_programs(config: ProjectConfig) -> dict:
    programs = dict(BASE_PROGRAMS)

    if config.esp_cam_base_url == DEFAULT_ESP_CAM_BASE_URL:
        print(
            "[WARNING] SAGRI_ESP_CAM_URL is not configured — "
            "esp_cam_scheduler.py will keep retrying until it's set."
        )

    if config.inference_enabled:
        programs["inference_worker.py"] = True
    else:
        print("[INFO] Inference worker disabled (SAGRI_ENABLE_INFERENCE=0).")

    if config.cloud_sync_enabled:
        programs["cloud_adapter.py"] = True
    else:
        print("[INFO] Cloud adapter disabled (SAGRI_ENABLE_CLOUD_SYNC=0).")

    return programs


def main() -> None:
    config = ProjectConfig.from_env()

    supervisor = ProcessSupervisor(config.project_directory, build_programs(config))

    print("=" * 50)
    print("RASPBERRY PI PROJECT SMART LAUNCHER")
    print("=" * 50)
    print()

    supervisor.start_all()
    supervisor.monitor_forever()


if __name__ == "__main__":
    main()
