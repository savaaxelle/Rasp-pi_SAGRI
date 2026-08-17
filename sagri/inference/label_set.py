from pathlib import Path


class LabelSet:
    """
    Loads class names from labels.txt.

    Example labels.txt:

    healthy
    leaf_blast
    brown_spot
    """

    def __init__(self, labels_file: Path):
        self._labels_file = labels_file
        self.labels = []

    def load(self) -> None:
        if not self._labels_file.exists():
            print("[INFO] Labels file not found:")
            print(f"       {self._labels_file}")
            print("[INFO] Generic class names will be used.")
            self.labels = []
            return

        with self._labels_file.open(mode="r", encoding="utf-8") as file:
            self.labels = [line.strip() for line in file if line.strip()]

        print(f"[OK] Loaded {len(self.labels)} labels.")
