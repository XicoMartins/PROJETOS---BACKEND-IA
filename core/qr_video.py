"""Leitura de QR Codes em quadros de video enviados pelo navegador."""

from __future__ import annotations

import threading

import av
import cv2
import numpy as np


def decode_qr_frame(image: np.ndarray, detector=None) -> tuple[str | None, np.ndarray | None]:
    """Retorna o texto e os cantos do primeiro QR encontrado no quadro."""
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        return None, None

    qr_detector = detector or cv2.QRCodeDetector()
    value, points, _ = qr_detector.detectAndDecode(image)
    value = str(value or "").strip()
    return (value or None), points


class QRVideoProcessor:
    """Procura QR Codes no video sem acessar o estado do Streamlit na thread."""

    def __init__(self) -> None:
        self._detector = cv2.QRCodeDetector()
        self._lock = threading.Lock()
        self._detected_value: str | None = None
        self._frame_count = 0

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        self._frame_count += 1

        # Ler um em cada quatro quadros reduz bastante o uso de CPU sem
        # prejudicar a experiencia de apontar a camera para um QR parado.
        if self._frame_count % 4:
            return frame

        image = frame.to_ndarray(format="bgr24")
        value, points = decode_qr_frame(image, self._detector)

        if not value:
            return frame

        with self._lock:
            if self._detected_value is None:
                self._detected_value = value

        if points is not None:
            corners = np.int32(points).reshape(-1, 2)
            cv2.polylines(image, [corners], True, (0, 200, 0), 4)

        return av.VideoFrame.from_ndarray(image, format="bgr24")

    def pop_detected_value(self) -> str | None:
        """Entrega uma leitura somente uma vez de forma segura entre threads."""
        with self._lock:
            value = self._detected_value
            self._detected_value = None
        return value
