from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2


Point = Tuple[int, int]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepara OpenTTGames no formato YOLO (classe: ball)")
    parser.add_argument("--dataset-root", default="datasets/OpenTTGames", help="Raiz do OpenTTGames")
    parser.add_argument("--output-dir", default="datasets/OpenTTGames/yolo_ball", help="Diretorio de saida YOLO")
    parser.add_argument("--bbox-size", type=int, default=14, help="Lado da caixa em pixels para a bola")
    parser.add_argument("--frame-step", type=int, default=2, help="Usa 1 a cada N frames anotados")
    parser.add_argument("--max-per-video", type=int, default=0, help="Limite de amostras por video (0 = sem limite)")
    return parser


def _load_ball_points(ball_markup_path: Path) -> Dict[int, Point]:
    with ball_markup_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    points: Dict[int, Point] = {}
    for frame_s, value in raw.items():
        x = int(value.get("x", -1))
        y = int(value.get("y", -1))
        if x < 0 or y < 0:
            continue
        points[int(frame_s)] = (x, y)
    return points


def _split_name(video_name: str) -> str:
    return "val" if video_name.startswith("test_") else "train"


def _save_yolo_sample(
    frame,
    point: Point,
    image_path: Path,
    label_path: Path,
    bbox_size: int,
) -> bool:
    h, w = frame.shape[:2]
    x, y = point

    half = bbox_size / 2.0
    x1 = max(0.0, x - half)
    y1 = max(0.0, y - half)
    x2 = min(float(w - 1), x + half)
    y2 = min(float(h - 1), y + half)

    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    xc = (x1 + x2) / 2.0
    yc = (y1 + y2) / 2.0

    if xc <= 0 or yc <= 0 or xc >= w or yc >= h:
        return False

    image_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.parent.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(image_path), frame)

    line = f"0 {xc / w:.6f} {yc / h:.6f} {bw / w:.6f} {bh / h:.6f}\n"
    with label_path.open("w", encoding="utf-8") as f:
        f.write(line)

    return True


def prepare_dataset(dataset_root: Path, output_dir: Path, bbox_size: int, frame_step: int, max_per_video: int) -> Dict[str, int]:
    videos_dir = dataset_root / "videos"
    markup_dir = dataset_root / "markup_extracted"

    if not videos_dir.exists():
        raise FileNotFoundError(f"Diretorio de videos nao encontrado: {videos_dir}")
    if not markup_dir.exists():
        raise FileNotFoundError(f"Diretorio de markup extraido nao encontrado: {markup_dir}")

    images_root = output_dir / "images"
    labels_root = output_dir / "labels"

    stats = {"train": 0, "val": 0}
    rebound_ground_truth: Dict[str, List[int]] = {}

    for video_path in sorted(videos_dir.glob("*.mp4")):
        video_name = video_path.stem
        split = _split_name(video_name)

        ball_markup_path = markup_dir / video_name / "ball_markup.json"
        events_markup_path = markup_dir / video_name / "events_markup.json"
        if not ball_markup_path.exists() or not events_markup_path.exists():
            continue

        points = _load_ball_points(ball_markup_path)
        if not points:
            continue

        with events_markup_path.open("r", encoding="utf-8") as f:
            events_raw = json.load(f)
        rebound_ground_truth[video_name] = sorted(
            int(frame) for frame, evt in events_raw.items() if str(evt).lower() in {"bounce", "net"}
        )

        selected = sorted(frame for frame in points if frame % frame_step == 0)
        if max_per_video > 0:
            selected = selected[:max_per_video]
        if not selected:
            continue

        selected_set = set(selected)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            continue

        frame_idx = 0
        saved = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_idx in selected_set:
                stem = f"{video_name}_{frame_idx:06d}"
                image_path = images_root / split / f"{stem}.jpg"
                label_path = labels_root / split / f"{stem}.txt"
                if _save_yolo_sample(frame, points[frame_idx], image_path, label_path, bbox_size):
                    saved += 1

            frame_idx += 1

        cap.release()
        stats[split] += saved

    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = output_dir / "dataset.yaml"
    yaml_text = "\n".join(
        [
            f"path: {output_dir.resolve()}",
            "train: images/train",
            "val: images/val",
            "names:",
            "  0: ball",
            "",
        ]
    )
    yaml_path.write_text(yaml_text, encoding="utf-8")

    gt_path = output_dir / "rebound_ground_truth.json"
    with gt_path.open("w", encoding="utf-8") as f:
        json.dump(rebound_ground_truth, f, indent=2, ensure_ascii=False)

    return stats


def main() -> None:
    args = build_parser().parse_args()
    dataset_root = Path(args.dataset_root)
    output_dir = Path(args.output_dir)

    stats = prepare_dataset(
        dataset_root=dataset_root,
        output_dir=output_dir,
        bbox_size=int(args.bbox_size),
        frame_step=max(1, int(args.frame_step)),
        max_per_video=max(0, int(args.max_per_video)),
    )

    print("Preparo concluido")
    print(f"- train_samples: {stats['train']}")
    print(f"- val_samples: {stats['val']}")
    print(f"- dataset_yaml: {output_dir / 'dataset.yaml'}")
    print(f"- rebound_ground_truth: {output_dir / 'rebound_ground_truth.json'}")


if __name__ == "__main__":
    main()
