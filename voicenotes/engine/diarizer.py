"""
Offline Speaker Diarization using CAM++ ONNX speaker embeddings
and Agglomerative Hierarchical Clustering.
100% offline, requires zero Hugging Face auth token.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import onnxruntime as ort
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from voicenotes.engine.audio_utils import compute_fbank
from voicenotes.engine.model_manager import ModelManager

logger = logging.getLogger(__name__)


class SpeakerDiarizer:
    """
    Offline speaker diarizer extracting speaker embeddings and clustering speech turns.
    """

    def __init__(self, model_path: Optional[Union[str, Path]] = None):
        if model_path is None:
            resolved = ModelManager.get_diarization_model_path()
            if resolved is None:
                # Attempt to download automatically
                resolved = ModelManager.download_diarization_model()
            self.model_path = Path(resolved)
        else:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Speaker diarization model not found at {self.model_path}. "
                "Run ModelManager.download_diarization_model() first."
            )

        # Set up ONNX Runtime session
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 2
        opts.intra_op_num_threads = 2
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        # Available execution providers
        providers = ["CPUExecutionProvider"]
        if "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=opts,
            providers=providers,
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def extract_embedding(self, audio_chunk: np.ndarray, sr: int = 16000) -> np.ndarray:
        """
        Extract a 512-dimensional speaker embedding from a raw audio segment.
        """
        if len(audio_chunk) < int(sr * 0.15):  # minimum 150ms of audio
            # Pad audio chunk to 0.2s with slight noise
            pad_len = int(sr * 0.2) - len(audio_chunk)
            audio_chunk = np.pad(audio_chunk, (0, pad_len), mode="constant")

        fbank = compute_fbank(audio_chunk, sr=sr)
        fbank_input = np.expand_dims(fbank, axis=0)  # [1, T, 80]

        outputs = self.session.run(
            [self.output_name],
            {self.input_name: fbank_input},
        )
        embedding = outputs[0][0]  # [512]
        # L2 normalize embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def diarize_segments(
        self,
        audio: np.ndarray,
        segments: List[Dict[str, Any]],
        sr: int = 16000,
        num_speakers: Optional[int] = None,
        distance_threshold: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """
        Assign speaker tags to a list of transcribed Whisper segments.

        Parameters:
        - audio: 1D float32 audio waveform at 16kHz
        - segments: list of dicts with 'start', 'end', 'text', etc.
        - sr: sample rate (16000)
        - num_speakers: fixed integer speaker count, or None for automatic discovery
        - distance_threshold: cosine distance threshold for automatic clustering (0.0 to 1.0)
        """
        if not segments:
            return []

        if len(segments) == 1:
            segments[0]["speaker"] = "Speaker 1"
            return segments

        embeddings = []
        valid_indices = []

        total_samples = len(audio)

        for idx, seg in enumerate(segments):
            start_sec = seg["start"]
            end_sec = seg["end"]
            start_idx = max(0, int(start_sec * sr))
            end_idx = min(total_samples, int(end_sec * sr))

            chunk = audio[start_idx:end_idx]
            # If segment is too short (< 0.25s), try slight context expansion
            if len(chunk) < int(sr * 0.25):
                pad_samples = int(sr * 0.2)
                start_idx = max(0, start_idx - pad_samples)
                end_idx = min(total_samples, end_idx + pad_samples)
                chunk = audio[start_idx:end_idx]

            if len(chunk) >= int(sr * 0.15):
                emb = self.extract_embedding(chunk, sr=sr)
                embeddings.append(emb)
                valid_indices.append(idx)
            else:
                # Segment was empty or zero
                embeddings.append(np.zeros(512, dtype=np.float32))

        embeddings_arr = np.array(embeddings)

        # Cluster embeddings
        n_samples = len(embeddings_arr)

        if num_speakers is not None and num_speakers > 0:
            actual_k = min(num_speakers, n_samples)
            if actual_k <= 1:
                labels = [0] * n_samples
            else:
                clustering = AgglomerativeClustering(
                    n_clusters=actual_k,
                    metric="cosine",
                    linkage="average",
                )
                labels = clustering.fit_predict(embeddings_arr).tolist()
        else:
            # Automatic clustering based on cosine distance threshold
            # Cosine distance = 1 - cosine_similarity
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                metric="cosine",
                linkage="average",
            )
            labels = clustering.fit_predict(embeddings_arr).tolist()

        # Re-map cluster IDs into chronological speaker numbers:
        # The first speaker heard is "Speaker 1", next new speaker is "Speaker 2", etc.
        speaker_map: Dict[int, str] = {}
        speaker_counter = 1

        for idx, seg in enumerate(segments):
            cluster_id = labels[idx]
            if cluster_id not in speaker_map:
                speaker_map[cluster_id] = f"Speaker {speaker_counter}"
                speaker_counter += 1
            seg["speaker"] = speaker_map[cluster_id]

        return segments
