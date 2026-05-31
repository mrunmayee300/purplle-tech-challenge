from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VisitorIdentity:
    visitor_id: str
    embedding: np.ndarray
    last_seen_ts: float
    exited_at: float | None = None


class ReIdentificationEngine:
    """OSNet when available; otherwise appearance + trajectory similarity."""

    def __init__(self, reentry_window_seconds: int = 900) -> None:
        self.reentry_window_seconds = reentry_window_seconds
        self._visitor_counter = 0
        self._active: dict[str, VisitorIdentity] = {}
        self._exited: list[VisitorIdentity] = []
        self._osnet = None
        self._use_osnet = False
        self._init_osnet()

    def _init_osnet(self) -> None:
        from shared.config import USE_OSNET

        if USE_OSNET in ("0", "false", "no"):
            return
        try:
            import torch
            from torchreid.reid.models import build_model
            from torchreid.reid.utils import load_pretrained_weights

            model = build_model(
                name="osnet_x0_25",
                num_classes=1,
                pretrained=False,
            )
            load_pretrained_weights(model, "osnet_x0_25_market1501.pth")
            model.eval()
            self._osnet = model
            self._use_osnet = True
            logger.info("OSNet re-identification enabled")
        except Exception as exc:
            logger.info("OSNet unavailable, using appearance fallback: %s", exc)

    def _next_visitor_id(self) -> str:
        self._visitor_counter += 1
        return f"v-{self._visitor_counter:04d}"

    def _appearance_embedding(self, crop: np.ndarray) -> np.ndarray:
        if crop.size == 0:
            return np.zeros(64, dtype=np.float32)
        if self._use_osnet and self._osnet is not None:
            import cv2
            import torch

            resized = cv2.resize(crop, (128, 256))
            tensor = torch.from_numpy(resized).float().permute(2, 0, 1) / 255.0
            tensor = tensor.unsqueeze(0)
            with torch.no_grad():
                feat = self._osnet(tensor)
            vec = feat.cpu().numpy().flatten().astype(np.float32)
            norm = np.linalg.norm(vec) + 1e-6
            return vec / norm
        hsv = cv2_hsv_histogram(crop)
        aspect = crop.shape[0] / max(crop.shape[1], 1)
        return np.concatenate([hsv, np.array([aspect], dtype=np.float32)])

    def assign_visitor(
        self,
        crop: np.ndarray,
        trajectory: list[tuple[float, float]],
        timestamp: float,
        is_exit: bool = False,
        visitor_id: str | None = None,
    ) -> tuple[str, bool]:
        """Returns (visitor_id, is_reentry)."""
        if is_exit and visitor_id and visitor_id in self._active:
            identity = self._active.pop(visitor_id)
            identity.exited_at = timestamp
            self._exited.append(identity)
            return visitor_id, False

        emb = self._appearance_embedding(crop)
        best_id: str | None = None
        best_score = 0.0
        is_reentry = False

        for visitor in self._exited:
            if visitor.exited_at is None:
                continue
            if timestamp - visitor.exited_at > self.reentry_window_seconds:
                continue
            score = _similarity(emb, visitor.embedding, trajectory, timestamp, visitor)
            if score > best_score and score >= 0.62:
                best_score = score
                best_id = visitor.visitor_id
                is_reentry = True

        if best_id:
            identity = next(v for v in self._exited if v.visitor_id == best_id)
            self._exited.remove(identity)
            identity.last_seen_ts = timestamp
            identity.exited_at = None
            identity.embedding = 0.7 * identity.embedding + 0.3 * emb
            self._active[best_id] = identity
            return best_id, is_reentry

        vid = self._next_visitor_id()
        identity = VisitorIdentity(
            visitor_id=vid, embedding=emb, last_seen_ts=timestamp
        )
        self._active[vid] = identity
        if is_exit:
            identity.exited_at = timestamp
            self._active.pop(vid)
            self._exited.append(identity)
        return vid, False


def cv2_hsv_histogram(crop: np.ndarray) -> np.ndarray:
    import cv2

    if crop.ndim == 2:
        crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist.astype(np.float32)


def _similarity(
    emb: np.ndarray,
    stored: np.ndarray,
    trajectory: list[tuple[float, float]],
    timestamp: float,
    visitor: VisitorIdentity,
) -> float:
    emb_score = float(np.dot(emb, stored))
    time_score = max(
        0.0, 1.0 - (timestamp - (visitor.exited_at or timestamp)) / 900.0
    )
    traj_score = 0.5
    if trajectory and len(trajectory) >= 2:
        traj_score = 0.7
    return 0.55 * emb_score + 0.25 * time_score + 0.2 * traj_score
