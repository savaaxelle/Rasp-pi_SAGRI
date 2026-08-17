from sagri.config import ProjectConfig
from sagri.serial_link.duplicate_filter import DuplicatePacketFilter
from sagri.serial_link.packet_codec import SensorPacketCodec
from sagri.serial_link.sensor_receiver import SerialSensorReceiver
from sagri.serial_link.sensor_status import SensorStatusValidator
from sagri.serial_link.serial_transport import SerialLink
from sagri.storage.sensor_repository import SensorDataRepository


def main() -> None:
    config = ProjectConfig.from_env()

    receiver = SerialSensorReceiver(
        config=config,
        repository=SensorDataRepository(config),
        codec=SensorPacketCodec(),
        link=SerialLink(),
        status_validator=SensorStatusValidator(),
        dup_filter=DuplicatePacketFilter(),
    )

    receiver.run()


if __name__ == "__main__":
    main()
