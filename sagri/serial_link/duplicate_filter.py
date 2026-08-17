from collections import deque

# Stores recent sequence numbers to prevent retransmitted packets
# from being saved more than once.
DEFAULT_HISTORY_SIZE = 500


class DuplicatePacketFilter:
    """Tracks recently seen sequence numbers to reject retransmits."""

    def __init__(self, history_size: int = DEFAULT_HISTORY_SIZE):
        self._seen_sequences = deque(maxlen=history_size)

    def is_duplicate(self, sequence) -> bool:
        return sequence in self._seen_sequences

    def remember(self, sequence) -> None:
        self._seen_sequences.append(sequence)
