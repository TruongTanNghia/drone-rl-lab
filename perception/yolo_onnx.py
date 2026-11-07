"""Chạy YOLO (ONNX, xuất từ Ultralytics) bằng onnxruntime trên CPU.

Đầu ra Ultralytics YOLO (v8/11/26 detect) sau export: tensor (1, 4+nc, N) với xywh ở tọa độ ảnh đã letterbox.
Hàm `detect` trả về danh sách (x0, y0, x1, y1, conf, cls) theo pixel ảnh gốc.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def letterbox(img: np.ndarray, size: int) -> tuple[np.ndarray, float, tuple[int, int]]:
    h, w = img.shape[:2]
    r = size / max(h, w)
    nh, nw = int(round(h * r)), int(round(w * r))
    import cv2  # chỉ import khi cần

    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR) if (nh, nw) != (h, w) else img
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    canvas[top : top + nh, left : left + nw] = resized
    return canvas, r, (left, top)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        xx0 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy0 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx1 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy1 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx1 - xx0, 0, None) * np.clip(yy1 - yy0, 0, None)
        a = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        b = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        iou = inter / (a + b - inter + 1e-9)
        order = rest[iou < iou_thr]
    return keep


class YoloOnnx:
    def __init__(self, model_path: str | Path, imgsz: int = 320, conf: float = 0.25, iou: float = 0.5, threads: int | None = None):
        import onnxruntime as ort

        so = ort.SessionOptions()
        if threads:
            so.intra_op_num_threads = int(threads)
        self.sess = ort.InferenceSession(str(model_path), sess_options=so, providers=["CPUExecutionProvider"])
        self.input_name = self.sess.get_inputs()[0].name
        shape = self.sess.get_inputs()[0].shape
        self.imgsz = int(shape[-1]) if isinstance(shape[-1], int) else imgsz
        self.conf = conf
        self.iou = iou
        self.providers = self.sess.get_providers()

    def detect(self, rgb: np.ndarray) -> list[tuple[float, float, float, float, float, int]]:
        canvas, r, (left, top) = letterbox(rgb, self.imgsz)
        x = canvas.astype(np.float32) / 255.0
        x = np.transpose(x, (2, 0, 1))[None]
        out = self.sess.run(None, {self.input_name: x})[0]
        pred = out[0]
        if pred.shape[0] < pred.shape[1]:  # (4+nc, N) -> (N, 4+nc)
            pred = pred.T
        xywh, cls_scores = pred[:, :4], pred[:, 4:]
        cls = cls_scores.argmax(axis=1)
        conf = cls_scores.max(axis=1)
        m = conf >= self.conf
        if not m.any():
            return []
        xywh, conf, cls = xywh[m], conf[m], cls[m]
        boxes = np.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2, xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], axis=1)
        keep = nms(boxes, conf, self.iou)
        res = []
        for i in keep:
            x0, y0, x1, y1 = boxes[i]
            res.append(((x0 - left) / r, (y0 - top) / r, (x1 - left) / r, (y1 - top) / r, float(conf[i]), int(cls[i])))
        return res
