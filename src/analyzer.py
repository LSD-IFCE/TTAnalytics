from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


BBox = Tuple[int, int, int, int]
Point = Tuple[int, int]
PointF = Tuple[float, float]


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: BBox


class TableTennisAnalyzer:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

        model_cfg = config.get("model", {})
        model_path = model_cfg.get("path", "yolov8n.pt")
        conf = float(model_cfg.get("conf_threshold", 0.25))
        iou = float(model_cfg.get("iou_threshold", 0.45))

        self.model = YOLO(model_path)
        self.model.overrides["conf"] = conf
        self.model.overrides["iou"] = iou

        analysis_cfg = config.get("analysis", {})
        self.ball_class_name = analysis_cfg.get("ball_class_name", "sports ball")
        self.ball_aliases = {"sports ball", "ball", "table tennis ball", "ping pong ball"}
        self.ball_class_id = self._resolve_class_id(self.ball_class_name)
        self.rally_gap_seconds = float(analysis_cfg.get("rally_gap_seconds", 0.7))
        self.min_rally_seconds = float(analysis_cfg.get("min_rally_seconds", 0.35))
        self.trail_size = int(analysis_cfg.get("trail_size", 20))
        self.table_length_m = float(analysis_cfg.get("table_length_m", 2.74))
        self.table_width_m = float(analysis_cfg.get("table_width_m", 1.525))
        self.rebound_min_gap_seconds = float(analysis_cfg.get("rebound_min_gap_seconds", 0.12))
        self.rebound_min_speed_px = float(analysis_cfg.get("rebound_min_speed_px", 2.0))
        self.rebound_min_vertical_turn_px = float(analysis_cfg.get("rebound_min_vertical_turn_px", 3.0))
        self.rebound_max_cosine = float(analysis_cfg.get("rebound_max_cosine", 0.55))
        self.rebound_table_margin_px = float(analysis_cfg.get("rebound_table_margin_px", 10.0))
        self.max_static_ball_frames = int(analysis_cfg.get("max_static_ball_frames", 6))
        self.static_center_epsilon_px = int(analysis_cfg.get("static_center_epsilon_px", 2))
        self.hotspot_bin_px = int(analysis_cfg.get("hotspot_bin_px", 4))
        self.hotspot_max_hits = int(analysis_cfg.get("hotspot_max_hits", 12))

        render_cfg = config.get("render", {})
        self.draw_trail = bool(render_cfg.get("draw_trail", True))
        self.draw_labels = bool(render_cfg.get("draw_labels", True))
        self.line_thickness = int(render_cfg.get("line_thickness", 2))
        self.font_scale = float(render_cfg.get("font_scale", 0.6))

    def analyze_video(
        self,
        video_path: str | Path,
        roi_bbox: BBox,
        table_points: List[Point],
        net_points: List[Point],
        output_video_path: Optional[str | Path] = None,
        output_json_path: Optional[str | Path] = None,
        output_heatmap_path: Optional[str | Path] = None,
        show: bool = False,
    ) -> Dict[str, Any]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Nao foi possivel abrir o video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        roi_bbox = self._clip_bbox_to_frame(roi_bbox, width, height)
        table_polygon = np.array(table_points, dtype=np.int32)
        table_h = self._compute_table_homography(table_points)
        net_line = self._fit_line_from_points(net_points)

        writer = None
        if output_video_path:
            output_video_path = Path(output_video_path)
            output_video_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

        ball_trail: deque[Optional[Point]] = deque(maxlen=self.trail_size)
        ball_positions: List[Optional[Point]] = []
        ball_positions_m: List[Optional[PointF]] = []
        speeds_px_s: List[float] = []
        speeds_km_h: List[float] = []
        touch_points: List[Point] = []
        touch_frames: List[int] = []

        min_rebound_gap_frames = max(1, int(self.rebound_min_gap_seconds * fps))
        last_rebound_frame = -min_rebound_gap_frames

        frames_processed = 0
        frames_with_ball = 0
        last_detected_center: Optional[Point] = None
        static_center_streak = 0
        hotspot_hits: Dict[Tuple[int, int], int] = {}

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            detections = self._infer(frame, roi_bbox)
            best_ball = self._select_ball_detection(detections, roi_bbox)

            ball_center = None
            if best_ball is not None:
                detected_center = self._bbox_center(best_ball.bbox)
                if last_detected_center is not None:
                    dx = abs(detected_center[0] - last_detected_center[0])
                    dy = abs(detected_center[1] - last_detected_center[1])
                    if dx <= self.static_center_epsilon_px and dy <= self.static_center_epsilon_px:
                        static_center_streak += 1
                    else:
                        static_center_streak = 1
                else:
                    static_center_streak = 1

                last_detected_center = detected_center

                bin_size = max(1, self.hotspot_bin_px)
                hotspot_key = (detected_center[0] // bin_size, detected_center[1] // bin_size)
                hotspot_hits[hotspot_key] = hotspot_hits.get(hotspot_key, 0) + 1
                is_hotspot = hotspot_hits[hotspot_key] > self.hotspot_max_hits

                if static_center_streak <= self.max_static_ball_frames and not is_hotspot:
                    ball_center = detected_center
                    frames_with_ball += 1
                    ball_trail.append(ball_center)
                else:
                    ball_trail.append(None)
            else:
                last_detected_center = None
                static_center_streak = 0
                ball_trail.append(None)

            ball_positions.append(ball_center)

            ball_center_m = None
            if ball_center is not None and table_h is not None and self._point_in_polygon(ball_center, table_polygon):
                ball_center_m = self._project_point_to_table_m(ball_center, table_h)
            ball_positions_m.append(ball_center_m)

            self._update_speed(speeds_px_s, speeds_km_h, ball_positions, ball_positions_m, fps)

            current_idx = len(ball_positions) - 1
            if (
                current_idx - last_rebound_frame >= min_rebound_gap_frames
                and self._is_rebound_index(ball_positions, current_idx, table_polygon)
            ):
                current_point = ball_positions[current_idx]
                if current_point is not None:
                    touch_points.append(current_point)
                    touch_frames.append(current_idx)
                    last_rebound_frame = current_idx

            annotated = self._mask_outside_roi(frame, roi_bbox)
            self._draw_scene(
                annotated,
                ball_center,
                speeds_px_s,
                speeds_km_h,
                roi_bbox,
                table_points,
                net_points,
                touch_points,
            )

            if writer is not None:
                writer.write(annotated)

            if show:
                cv2.imshow("YoloTT", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frames_processed += 1

        cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()

        heatmap_saved_path = None
        if output_heatmap_path:
            output_heatmap_path = Path(output_heatmap_path)
            output_heatmap_path.parent.mkdir(parents=True, exist_ok=True)
            heatmap_img = self._build_touch_heatmap_image(width, height, table_points, net_points, touch_points)
            cv2.imwrite(str(output_heatmap_path), heatmap_img)
            heatmap_saved_path = str(output_heatmap_path)

        metrics = self._compute_metrics(
            fps=fps,
            frames_processed=frames_processed,
            total_frames=total_frames,
            frames_with_ball=frames_with_ball,
            speeds_px_s=speeds_px_s,
            speeds_km_h=speeds_km_h,
            ball_positions=ball_positions,
            table_polygon=table_polygon,
            table_h=table_h,
            net_line=net_line,
            touch_points=touch_points,
            touch_frames=touch_frames,
            heatmap_path=heatmap_saved_path,
        )

        if output_json_path:
            output_json_path = Path(output_json_path)
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            with output_json_path.open("w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

        return metrics

    def _infer(self, frame: np.ndarray, roi_bbox: Optional[BBox] = None) -> List[Detection]:
        x_offset = 0
        y_offset = 0
        input_frame = frame

        if roi_bbox is not None:
            rx1, ry1, rx2, ry2 = roi_bbox
            input_frame = frame[ry1:ry2, rx1:rx2]
            x_offset = rx1
            y_offset = ry1

            if input_frame.size == 0:
                return []

        infer_kwargs: Dict[str, Any] = {"verbose": False}
        if self.ball_class_id is not None:
            infer_kwargs["classes"] = [self.ball_class_id]

        result = self.model(input_frame, **infer_kwargs)[0]
        names = result.names

        detections: List[Detection] = []
        if result.boxes is None:
            return detections

        for box in result.boxes:
            cls_id = int(box.cls.item())
            conf = float(box.conf.item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
            detections.append(
                Detection(
                    class_name=class_name,
                    confidence=conf,
                    bbox=(int(x1) + x_offset, int(y1) + y_offset, int(x2) + x_offset, int(y2) + y_offset),
                )
            )
        return detections

    def _select_ball_detection(
        self,
        detections: List[Detection],
        roi_bbox: BBox,
    ) -> Optional[Detection]:
        filtered = [d for d in detections if self._point_in_bbox(self._bbox_center(d.bbox), roi_bbox)]
        balls = [d for d in filtered if self._is_ball_class(d.class_name)]
        return max(balls, key=lambda d: d.confidence) if balls else None

    def _draw_scene(
        self,
        frame: np.ndarray,
        ball_center: Optional[Point],
        speeds_px_s: List[float],
        speeds_km_h: List[float],
        roi_bbox: BBox,
        table_points: List[Point],
        net_points: List[Point],
        touch_points: List[Point],
    ) -> None:
        cv2.rectangle(frame, (roi_bbox[0], roi_bbox[1]), (roi_bbox[2], roi_bbox[3]), (50, 255, 50), 2)

        if len(table_points) == 4 and len(net_points) == 4:
            self._draw_player_sides(frame, table_points, net_points)
            self._draw_net_marker(frame, net_points)
        elif len(table_points) == 4:
            cv2.polylines(frame, [np.array(table_points, dtype=np.int32)], True, (255, 190, 80), 2, cv2.LINE_AA)

        if ball_center is not None:
            self._draw_ball_highlight(frame, ball_center)

        current_speed = speeds_px_s[-1] if speeds_px_s else 0.0
        avg_speed = float(np.mean(speeds_px_s)) if speeds_px_s else 0.0
        current_speed_kmh = speeds_km_h[-1] if speeds_km_h else 0.0
        avg_speed_kmh = float(np.mean(speeds_km_h)) if speeds_km_h else 0.0
        hud = [
            f"Velocidade bola (px/s): {current_speed:.1f}",
            f"Media velocidade (px/s): {avg_speed:.1f}",
            f"Velocidade bola (km/h): {current_speed_kmh:.1f}",
            f"Media velocidade (km/h): {avg_speed_kmh:.1f}",
        ]

        y = 28
        for line in hud:
            if not line:
                continue
            cv2.putText(
                frame,
                line,
                (12, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.font_scale,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            y += 26

    def _draw_touch_marks(self, frame: np.ndarray, touch_points: List[Point]) -> None:
        for idx, p in enumerate(touch_points, start=1):
            x, y = int(p[0]), int(p[1])
            cv2.circle(frame, (x, y), 8, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 6, (0, 70, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 10, (255, 255, 255), 1, cv2.LINE_AA)
            if idx % 5 == 0:
                cv2.putText(
                    frame,
                    str(idx),
                    (x + 8, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

    def _draw_player_sides(self, frame: np.ndarray, table_points: List[Point], net_points: List[Point]) -> None:
        table_poly = np.array(table_points, dtype=np.int32)
        cv2.polylines(frame, [table_poly], True, (255, 190, 80), 2, cv2.LINE_AA)

        net_line = self._fit_line_from_points(net_points)
        if net_line is None:
            return

        ordered = self._order_points(np.array(table_points, dtype=np.float32))
        side_polys = self._split_table_by_net(ordered, net_line)
        if side_polys is not None:
            overlay = frame.copy()
            poly_a, poly_b = side_polys
            cv2.fillConvexPoly(overlay, poly_a.astype(np.int32), (70, 110, 230))
            cv2.fillConvexPoly(overlay, poly_b.astype(np.int32), (70, 185, 90))
            cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)

            pos_center = np.mean(poly_a, axis=0)
            neg_center = np.mean(poly_b, axis=0)
            self._draw_text_badge(frame, "lado_a", (int(pos_center[0]), int(pos_center[1])), (70, 110, 230))
            self._draw_text_badge(frame, "lado_b", (int(neg_center[0]), int(neg_center[1])), (70, 185, 90))
            return

        a, b, c = net_line
        pts = np.array(table_points, dtype=np.float32)
        signed = a * pts[:, 0] + b * pts[:, 1] + c

        pos_pts = pts[signed >= 0]
        neg_pts = pts[signed < 0]

        if len(pos_pts) == 0 or len(neg_pts) == 0:
            center_y = float(np.mean(pts[:, 1]))
            pos_pts = pts[pts[:, 1] <= center_y]
            neg_pts = pts[pts[:, 1] > center_y]
            if len(pos_pts) == 0 or len(neg_pts) == 0:
                return

        pos_center = np.mean(pos_pts, axis=0)
        neg_center = np.mean(neg_pts, axis=0)

        self._draw_text_badge(frame, "lado_a", (int(pos_center[0]), int(pos_center[1])), (70, 110, 230))
        self._draw_text_badge(frame, "lado_b", (int(neg_center[0]), int(neg_center[1])), (70, 185, 90))

    def _draw_net_marker(self, frame: np.ndarray, net_points: List[Point]) -> None:
        pts = np.array(net_points, dtype=np.int32)
        cv2.polylines(frame, [pts], True, (80, 210, 255), 2, cv2.LINE_AA)
        for p in pts:
            cv2.circle(frame, (int(p[0]), int(p[1])), 4, (80, 210, 255), -1, cv2.LINE_AA)

        centroid = np.mean(pts, axis=0)
        cx, cy = int(centroid[0]), int(centroid[1])
        self._draw_text_badge(frame, "rede", (cx + 20, cy - 8), (80, 210, 255))

    def _draw_ball_highlight(self, frame: np.ndarray, center: Point) -> None:
        # Marker intentionally minimal to avoid occluding the ball.
        cv2.circle(frame, center, 5, (0, 165, 255), -1, cv2.LINE_AA)

    @staticmethod
    def _draw_text_badge(
        frame: np.ndarray,
        text: str,
        anchor: Point,
        bg_color: Tuple[int, int, int],
    ) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

        x = int(anchor[0])
        y = int(anchor[1])
        x1 = max(0, x - 4)
        y1 = max(0, y - th - baseline - 4)
        x2 = min(frame.shape[1] - 1, x + tw + 6)
        y2 = min(frame.shape[0] - 1, y + 4)

        cv2.rectangle(frame, (x1, y1), (x2, y2), bg_color, -1, cv2.LINE_AA)
        cv2.putText(frame, text, (x, y - 2), font, scale, (20, 20, 20), thickness, cv2.LINE_AA)

    def _mask_outside_roi(self, frame: np.ndarray, roi_bbox: BBox) -> np.ndarray:
        masked = np.zeros_like(frame)
        x1, y1, x2, y2 = roi_bbox
        masked[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
        return masked

    def _draw_bbox(self, frame: np.ndarray, det: Detection, color: Tuple[int, int, int], label: str) -> None:
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.line_thickness)
        if self.draw_labels:
            text = f"{label} {det.confidence:.2f}"
            cv2.putText(
                frame,
                text,
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.font_scale,
                color,
                2,
                cv2.LINE_AA,
            )

    def _draw_ball_trail(self, frame: np.ndarray, trail: deque[Optional[Point]]) -> None:
        valid_points = [pt for pt in trail if pt is not None]
        for i in range(1, len(valid_points)):
            cv2.line(frame, valid_points[i - 1], valid_points[i], (0, 255, 255), 2)

    def _update_speed(
        self,
        speeds_px_s: List[float],
        speeds_km_h: List[float],
        positions_px: List[Optional[Point]],
        positions_m: List[Optional[PointF]],
        fps: float,
    ) -> None:
        if len(positions_px) < 2:
            return

        p1 = positions_px[-2]
        p2 = positions_px[-1]
        if p1 is None or p2 is None:
            return

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = float(np.sqrt(dx * dx + dy * dy))
        speeds_px_s.append(dist * fps)

        if len(positions_m) < 2:
            return

        m1 = positions_m[-2]
        m2 = positions_m[-1]
        if m1 is None or m2 is None:
            return

        mdx = m2[0] - m1[0]
        mdy = m2[1] - m1[1]
        dist_m = float(np.sqrt(mdx * mdx + mdy * mdy))
        speed_km_h = dist_m * fps * 3.6
        speeds_km_h.append(speed_km_h)

    def _compute_metrics(
        self,
        fps: float,
        frames_processed: int,
        total_frames: int,
        frames_with_ball: int,
        speeds_px_s: List[float],
        speeds_km_h: List[float],
        ball_positions: List[Optional[Point]],
        table_polygon: np.ndarray,
        table_h: Optional[np.ndarray],
        net_line: Optional[Tuple[float, float, float]],
        touch_points: List[Point],
        touch_frames: List[int],
        heatmap_path: Optional[str],
    ) -> Dict[str, Any]:
        rally_gap_frames = max(1, int(self.rally_gap_seconds * fps))
        min_rally_frames = max(1, int(self.min_rally_seconds * fps))

        rallies = self._estimate_rallies(ball_positions, rally_gap_frames, min_rally_frames)
        touch_events = self._build_touch_events(touch_frames, touch_points, fps, table_h, net_line)
        touches_by_side = {
            "lado_a": [evt for evt in touch_events if evt["side"] == "lado_a"],
            "lado_b": [evt for evt in touch_events if evt["side"] == "lado_b"],
            "indefinido": [evt for evt in touch_events if evt["side"] == "indefinido"],
        }
        total_rally_time_s = sum((end - start + 1) / fps for start, end in rallies)

        return {
            "frames_processed": frames_processed,
            "video_frames_reported": total_frames,
            "fps": fps,
            "ball_class_name": self.ball_class_name,
            "ball_class_id": self.ball_class_id,
            "ball_class_found_in_model": self.ball_class_id is not None,
            "ball_detection_rate": (frames_with_ball / frames_processed) if frames_processed else 0.0,
            "estimated_rallies": len(rallies),
            "estimated_rally_time_seconds": total_rally_time_s,
            "estimated_rebounds": len(touch_events),
            "rebound_timestamps_seconds": [evt["timestamp_seconds"] for evt in touch_events],
            "touch_events": touch_events,
            "touches_by_side": touches_by_side,
            "touch_points_count": len(touch_points),
            "touch_heatmap_path": heatmap_path,
            "rebound_criteria": {
                "min_gap_seconds": self.rebound_min_gap_seconds,
                "min_speed_px": self.rebound_min_speed_px,
                "min_vertical_turn_px": self.rebound_min_vertical_turn_px,
                "max_cosine_for_turn": self.rebound_max_cosine,
                "table_margin_px": self.rebound_table_margin_px,
                "logic": "pico_ou_inversao_vertical_ou_quebra_angular_com_velocidade_minima",
            },
            "avg_ball_speed_px_s": float(np.mean(speeds_px_s)) if speeds_px_s else 0.0,
            "max_ball_speed_px_s": float(np.max(speeds_px_s)) if speeds_px_s else 0.0,
            "avg_ball_speed_km_h": float(np.mean(speeds_km_h)) if speeds_km_h else 0.0,
            "max_ball_speed_km_h": float(np.max(speeds_km_h)) if speeds_km_h else 0.0,
            "table_dimensions_m": {
                "length": self.table_length_m,
                "width": self.table_width_m,
            },
        }

    def _estimate_rallies(
        self,
        ball_positions: List[Optional[Point]],
        rally_gap_frames: int,
        min_rally_frames: int,
    ) -> List[Tuple[int, int]]:
        rallies: List[Tuple[int, int]] = []
        start = None
        last_seen = None

        for i, pos in enumerate(ball_positions):
            if pos is not None:
                if start is None:
                    start = i
                last_seen = i
                continue

            if start is not None and last_seen is not None and i - last_seen > rally_gap_frames:
                if last_seen - start + 1 >= min_rally_frames:
                    rallies.append((start, last_seen))
                start = None
                last_seen = None

        if start is not None and last_seen is not None and last_seen - start + 1 >= min_rally_frames:
            rallies.append((start, last_seen))

        return rallies

    def _estimate_rebounds(
        self,
        ball_positions: List[Optional[Point]],
        fps: float,
        table_polygon: Optional[np.ndarray] = None,
    ) -> List[int]:
        min_gap_frames = max(1, int(self.rebound_min_gap_seconds * fps))
        rebounds: List[int] = []
        last_added = -min_gap_frames

        for idx in range(2, len(ball_positions) - 1):
            if not self._is_rebound_index(ball_positions, idx, table_polygon):
                continue
            if idx - last_added < min_gap_frames:
                continue

            rebounds.append(idx)
            last_added = idx

        return rebounds

    def _is_rebound_index(
        self,
        ball_positions: List[Optional[Point]],
        idx: int,
        table_polygon: Optional[np.ndarray] = None,
    ) -> bool:
        if idx < 2 or idx + 1 >= len(ball_positions):
            return False

        p_prev = ball_positions[idx - 1]
        p_curr = ball_positions[idx]
        p_next = ball_positions[idx + 1]
        if p_prev is None or p_curr is None or p_next is None:
            return False

        vx1 = p_curr[0] - p_prev[0]
        vx2 = p_next[0] - p_curr[0]
        vy1 = p_curr[1] - p_prev[1]
        vy2 = p_next[1] - p_curr[1]

        speed1 = float(np.sqrt(vx1 * vx1 + vy1 * vy1))
        speed2 = float(np.sqrt(vx2 * vx2 + vy2 * vy2))
        if speed1 < self.rebound_min_speed_px or speed2 < self.rebound_min_speed_px:
            return False

        vertical_flip = (vy1 > 0 and vy2 < 0) and (abs(vy1) + abs(vy2) >= self.rebound_min_vertical_turn_px)

        local_peak = (
            p_curr[1] >= p_prev[1]
            and p_curr[1] >= p_next[1]
            and (p_curr[1] - p_prev[1] + p_curr[1] - p_next[1] >= self.rebound_min_vertical_turn_px)
        )

        dot = float(vx1 * vx2 + vy1 * vy2)
        denom = speed1 * speed2
        turn_cos = (dot / denom) if denom > 1e-9 else 1.0
        strong_turn = turn_cos <= self.rebound_max_cosine

        direction_flip_x = (vx1 * vx2 < 0) and (abs(vx1) + abs(vx2) >= 6)
        if not (vertical_flip or local_peak or strong_turn or direction_flip_x):
            return False

        if table_polygon is not None and not self._point_near_polygon(p_curr, table_polygon, self.rebound_table_margin_px):
            return False
        return True

    def _build_touch_events(
        self,
        touch_frames: List[int],
        touch_points: List[Point],
        fps: float,
        table_h: Optional[np.ndarray],
        net_line: Optional[Tuple[float, float, float]],
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for idx, p in zip(touch_frames, touch_points):

            side = self._classify_side_by_net(p, net_line)
            evt: Dict[str, Any] = {
                "frame": idx,
                "timestamp_seconds": round(idx / fps, 3),
                "pixel_point": [int(p[0]), int(p[1])],
                "side": side,
            }

            if table_h is not None:
                p_m = self._project_point_to_table_m(p, table_h)
                evt["table_point_m"] = [round(p_m[0], 3), round(p_m[1], 3)]

            events.append(evt)

        return events

    def _build_touch_heatmap_image(
        self,
        width: int,
        height: int,
        table_points: List[Point],
        net_points: List[Point],
        touch_points: List[Point],
    ) -> np.ndarray:
        heat = np.zeros((height, width), dtype=np.float32)
        for x, y in touch_points:
            if 0 <= x < width and 0 <= y < height:
                cv2.circle(heat, (int(x), int(y)), 18, 1.0, -1, cv2.LINE_AA)

        heat = cv2.GaussianBlur(heat, (0, 0), sigmaX=14, sigmaY=14)

        if np.max(heat) > 0:
            heat_norm = np.uint8(np.clip((heat / np.max(heat)) * 255.0, 0, 255))
        else:
            heat_norm = np.zeros_like(heat, dtype=np.uint8)

        heat_color = cv2.applyColorMap(heat_norm, cv2.COLORMAP_JET)

        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        if len(table_points) == 4:
            table_poly = np.array(table_points, dtype=np.int32)
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.fillConvexPoly(mask, table_poly, 255)
            canvas[mask > 0] = heat_color[mask > 0]
            cv2.polylines(canvas, [table_poly], True, (255, 255, 255), 2, cv2.LINE_AA)

        if len(net_points) == 4:
            net_poly = np.array(net_points, dtype=np.int32)
            cv2.polylines(canvas, [net_poly], True, (240, 240, 240), 2, cv2.LINE_AA)

        self._draw_text_badge(canvas, "mapa de calor - toques na mesa", (12, 28), (220, 220, 220))
        self._draw_text_badge(canvas, f"toques: {len(touch_points)}", (12, 54), (220, 220, 220))
        return canvas

    def _compute_table_homography(self, table_points: List[Point]) -> Optional[np.ndarray]:
        if len(table_points) != 4:
            return None

        src = self._order_points(np.array(table_points, dtype=np.float32))
        dst = np.array(
            [
                [0.0, 0.0],
                [self.table_length_m, 0.0],
                [self.table_length_m, self.table_width_m],
                [0.0, self.table_width_m],
            ],
            dtype=np.float32,
        )

        h, _ = cv2.findHomography(src, dst, method=0)
        return h

    @staticmethod
    def _fit_line_from_points(points: List[Point]) -> Optional[Tuple[float, float, float]]:
        if len(points) < 2:
            return None

        pts = np.array(points, dtype=np.float32)
        line = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
        vx, vy, x0, y0 = [float(v) for v in line.flatten()]
        a = vy
        b = -vx
        c = -(a * x0 + b * y0)
        norm = float(np.sqrt(a * a + b * b))
        if norm <= 1e-9:
            return None
        return (a / norm, b / norm, c / norm)

    @staticmethod
    def _classify_side_by_net(point: Point, net_line: Optional[Tuple[float, float, float]]) -> str:
        if net_line is None:
            return "indefinido"

        a, b, c = net_line
        signed_dist = a * point[0] + b * point[1] + c
        if signed_dist > 0:
            return "lado_a"
        if signed_dist < 0:
            return "lado_b"
        return "indefinido"

    @staticmethod
    def _project_point_to_table_m(point: Point, homography: np.ndarray) -> PointF:
        src = np.array([[[float(point[0]), float(point[1])]]], dtype=np.float32)
        dst = cv2.perspectiveTransform(src, homography)
        x_m, y_m = dst[0, 0]
        return (float(x_m), float(y_m))

    @staticmethod
    def _point_in_polygon(point: Point, polygon: np.ndarray) -> bool:
        if polygon is None or len(polygon) < 3:
            return False
        return cv2.pointPolygonTest(polygon.astype(np.float32), (float(point[0]), float(point[1])), False) >= 0

    @staticmethod
    def _point_near_polygon(point: Point, polygon: np.ndarray, margin_px: float) -> bool:
        if polygon is None or len(polygon) < 3:
            return False
        dist = cv2.pointPolygonTest(
            polygon.astype(np.float32),
            (float(point[0]), float(point[1])),
            True,
        )
        return dist >= -abs(float(margin_px))

    @staticmethod
    def _order_points(points: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype=np.float32)
        s = points.sum(axis=1)
        rect[0] = points[np.argmin(s)]
        rect[2] = points[np.argmax(s)]

        diff = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diff)]
        rect[3] = points[np.argmax(diff)]
        return rect

    def _resolve_class_id(self, class_name: str) -> Optional[int]:
        names = getattr(self.model, "names", None)
        target = class_name.strip().lower()

        if isinstance(names, dict):
            for cls_id, cls_name in names.items():
                if str(cls_name).strip().lower() == target:
                    return int(cls_id)
            for cls_id, cls_name in names.items():
                if str(cls_name).strip().lower() in self.ball_aliases:
                    return int(cls_id)
            return None

        if isinstance(names, list):
            for cls_id, cls_name in enumerate(names):
                if str(cls_name).strip().lower() == target:
                    return cls_id
            for cls_id, cls_name in enumerate(names):
                if str(cls_name).strip().lower() in self.ball_aliases:
                    return cls_id

        return None

    def _is_ball_class(self, class_name: str) -> bool:
        normalized = class_name.strip().lower()
        target = self.ball_class_name.strip().lower()
        return normalized == target or normalized in self.ball_aliases

    @staticmethod
    def _split_table_by_net(
        ordered_table: np.ndarray,
        net_line: Tuple[float, float, float],
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        a, b, c = net_line
        table = ordered_table.reshape(4, 2)

        def sign(p: np.ndarray) -> float:
            return float(a * p[0] + b * p[1] + c)

        intersections: List[np.ndarray] = []
        for i in range(4):
            p1 = table[i]
            p2 = table[(i + 1) % 4]
            d1 = sign(p1)
            d2 = sign(p2)

            if abs(d1) <= 1e-6 and abs(d2) <= 1e-6:
                continue
            if d1 * d2 > 0:
                continue

            denom = (d1 - d2)
            if abs(denom) <= 1e-9:
                continue
            t = d1 / denom
            t = max(0.0, min(1.0, t))
            inter = p1 + t * (p2 - p1)
            intersections.append(inter)

        unique_inters: List[np.ndarray] = []
        for p in intersections:
            if not any(np.linalg.norm(p - q) < 2.0 for q in unique_inters):
                unique_inters.append(p)

        if len(unique_inters) < 2:
            return None

        inter_a, inter_b = unique_inters[0], unique_inters[1]

        pos_pts: List[np.ndarray] = []
        neg_pts: List[np.ndarray] = []
        for p in table:
            d = sign(p)
            if d >= 0:
                pos_pts.append(p)
            if d <= 0:
                neg_pts.append(p)

        pos_pts.extend([inter_a, inter_b])
        neg_pts.extend([inter_a, inter_b])

        if len(pos_pts) < 3 or len(neg_pts) < 3:
            return None

        poly_a = cv2.convexHull(np.array(pos_pts, dtype=np.float32)).reshape(-1, 2)
        poly_b = cv2.convexHull(np.array(neg_pts, dtype=np.float32)).reshape(-1, 2)
        return poly_a, poly_b

    @staticmethod
    def _bbox_center(bbox: BBox) -> Point:
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    @staticmethod
    def _point_in_bbox(point: Point, bbox: BBox) -> bool:
        x, y = point
        x1, y1, x2, y2 = bbox
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _clip_bbox_to_frame(bbox: BBox, width: int, height: int) -> BBox:
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(x1 + 1, min(x2, width))
        y2 = max(y1 + 1, min(y2, height))
        return (x1, y1, x2, y2)


