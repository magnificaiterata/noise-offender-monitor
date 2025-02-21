import numpy as np
import wave
from edge_impulse_linux.runner import ImpulseRunner


class AudioFileProcessor:
    def __init__(self, model_path):
        self.runner = ImpulseRunner(model_path)
        self.window_size = 0
        self.overlap = 0.25
        self.sampling_rate = 0
        self.labels = []

    def init_model(self):
        model_info = self.runner.init()
        self.window_size = model_info['model_parameters']['input_features_count']
        self.sampling_rate = model_info['model_parameters']['frequency']
        self.labels = model_info['model_parameters']['labels']

    def process_audio(self, file_path):
        with wave.open(file_path, 'rb') as wf:
            rate = wf.getframerate()
            assert rate == self.sampling_rate, f"Expected {self.sampling_rate} Hz, got {rate} Hz"
            frames = wf.readframes(wf.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)

        features = np.array([], dtype=np.int16)
        all_results = []

        for i in range(0, len(data) - self.window_size, int(self.window_size * self.overlap)):
            window = data[i:i + self.window_size].tolist()
            res = self.runner.classify(window)
            scores = res['result']['classification']
            all_results.append(scores)

        avg_scores = {label: np.mean([res.get(label, 0) for res in all_results]) for label in self.labels}
        best_label = max(avg_scores, key=avg_scores.get)

        return best_label, avg_scores[best_label]

