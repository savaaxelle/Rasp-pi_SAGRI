import numpy as np

from sagri.inference.label_set import LabelSet


class PredictionDecoder:
    """Decodes a raw model prediction into (class_index, label, confidence)."""

    def __init__(self, label_set: LabelSet):
        self._label_set = label_set

    @staticmethod
    def softmax(values) -> np.ndarray:
        """Convert logits into multiclass probabilities."""

        values = np.asarray(values, dtype=np.float64)
        values = values - np.max(values)
        exp_values = np.exp(values)

        return exp_values / np.sum(exp_values)

    @staticmethod
    def sigmoid(value) -> float:
        """Convert binary logit into probability."""

        return float(1.0 / (1.0 + np.exp(-value)))

    def decode(self, prediction) -> tuple:
        prediction = np.asarray(prediction).squeeze()

        if prediction.ndim == 0:
            class_index, confidence = self._decode_binary(prediction)
        else:
            class_index, confidence = self._decode_multiclass(prediction)

        labels = self._label_set.labels

        if 0 <= class_index < len(labels):
            label = labels[class_index]
        else:
            # Temporary class name until labels are supplied.
            label = f"class_{class_index}"

        return class_index, label, confidence

    def _decode_binary(self, prediction) -> tuple:
        value = float(prediction)

        # Check whether model already returns probability.
        if 0.0 <= value <= 1.0:
            positive_probability = value
        else:
            positive_probability = self.sigmoid(value)

        if positive_probability >= 0.5:
            return 1, positive_probability

        return 0, 1.0 - positive_probability

    def _decode_multiclass(self, prediction) -> tuple:
        probabilities = prediction.astype(np.float64).reshape(-1)

        looks_like_probabilities = (
            np.all(probabilities >= 0.0)
            and np.all(probabilities <= 1.0)
            and np.isclose(probabilities.sum(), 1.0, atol=1e-3)
        )

        # If output is logits, convert using softmax.
        if not looks_like_probabilities:
            probabilities = self.softmax(probabilities)

        class_index = int(np.argmax(probabilities))
        confidence = float(probabilities[class_index])

        return class_index, confidence
