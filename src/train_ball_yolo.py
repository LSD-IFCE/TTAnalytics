from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fine-tuning YOLO para detectar a bolinha no OpenTTGames")
    parser.add_argument("--data", default="datasets/OpenTTGames/yolo_ball/dataset.yaml", help="YAML do dataset YOLO")
    parser.add_argument("--model", default="yolov8n.pt", help="Checkpoint inicial")
    parser.add_argument("--epochs", type=int, default=12, help="Numero de epocas")
    parser.add_argument("--imgsz", type=int, default=960, help="Resolucao de treino")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--project", default="outputs/train", help="Diretorio de resultados")
    parser.add_argument("--name", default="openttgames_ball", help="Nome da execucao")
    parser.add_argument("--device", default="cpu", help="Dispositivo (cpu, 0, 0,1...)" )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=int(args.epochs),
        imgsz=int(args.imgsz),
        batch=int(args.batch),
        project=args.project,
        name=args.name,
        device=args.device,
        pretrained=True,
        workers=2,
        cache=False,
    )

    run_dir = Path(model.trainer.save_dir) / "weights"
    best = run_dir / "best.pt"
    if best.exists():
        out = Path("outputs/weights/yolo_ball_openttgames.pt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(best.read_bytes())
        print(f"Modelo salvo em: {out}")
    else:
        print(f"Nao foi encontrado best.pt em: {run_dir}")


if __name__ == "__main__":
    main()
