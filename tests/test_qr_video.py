import unittest

import cv2
import numpy as np
import qrcode

from core.qr_video import decode_qr_frame


class QrVideoTests(unittest.TestCase):
    def test_decodes_process_id_from_camera_frame(self):
        qr_image = qrcode.make("000038").convert("RGB")
        rgb = np.asarray(qr_image)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        value, points = decode_qr_frame(bgr)

        self.assertEqual(value, "000038")
        self.assertIsNotNone(points)

    def test_returns_none_when_frame_has_no_qr(self):
        blank = np.full((400, 400, 3), 255, dtype=np.uint8)

        value, points = decode_qr_frame(blank)

        self.assertIsNone(value)
        self.assertIsNone(points)


if __name__ == "__main__":
    unittest.main()
