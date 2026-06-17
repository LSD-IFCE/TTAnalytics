from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from config import load_config
from analyzer import TableTennisAnalyzer


BBox = Tuple[int, int, int, int]
Point = Tuple[int, int]


def _parse_bbox(values: object, name: str) -> BBox:
    if not isinstance(values, list) or len(values) != 4:
        raise ValueError(f"Campo '{name}' deve ser uma lista com 4 inteiros.")

    try:
        x1, y1, x2, y2 = [int(v) for v in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo '{name}' contem valores invalidos.") from exc

    return (x1, y1, x2, y2)


def _parse_points(values: object, name: str, expected_len: int = 4) -> List[Point]:
    if not isinstance(values, list) or len(values) != expected_len:
        raise ValueError(f"Campo '{name}' deve ser uma lista com {expected_len} pontos.")

    points: List[Point] = []
    for i, p in enumerate(values):
        if not isinstance(p, list) or len(p) != 2:
            raise ValueError(f"Campo '{name}[{i}]' deve conter [x, y].")
        try:
            x, y = int(p[0]), int(p[1])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Campo '{name}[{i}]' contem valores invalidos.") from exc
        points.append((x, y))

    return points


def load_regions(regions_path: str | Path) -> Dict[str, object]:
    path = Path(regions_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de regioes nao encontrado: {path}. Rode antes: python src/select_regions_gui.py --video <video>"
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("JSON de regioes invalido: objeto raiz deve ser um dicionario.")

    roi_bbox = _parse_bbox(data.get("roi_bbox"), "roi_bbox")
    table_points = _parse_points(data.get("table_points"), "table_points", expected_len=4)
    net_points = _parse_points(data.get("net_points"), "net_points", expected_len=4)

    return {
        "roi_bbox": roi_bbox,
        "table_points": table_points,
        "net_points": net_points,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analise de tenis de mesa com YOLO e OpenCV"
    )
    parser.add_argument("--video", required=True, help="Caminho para o video de entrada")
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Arquivo de configuracao YAML",
    )
    parser.add_argument(
        "--output-video",
        default="outputs/analise.mp4",
        help="Caminho do video anotado de saida",
    )
    parser.add_argument(
        "--output-json",
        default="outputs/metricas.json",
        help="Caminho do JSON com metricas",
    )
    parser.add_argument(
        "--output-heatmap",
        default="outputs/heatmap_toques.png",
        help="Caminho da imagem PNG do mapa de calor de toques na mesa",
    )
    parser.add_argument(
        "--regions-json",
        default="outputs/regions.json",
        help="JSON com roi_bbox gerado por src/select_regions_gui.py",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Exibe o video em tempo real durante a analise",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    regions = load_regions(args.regions_json)
    analyzer = TableTennisAnalyzer(config)

    metrics = analyzer.analyze_video(
        video_path=Path(args.video),
        roi_bbox=regions["roi_bbox"],
        table_points=regions["table_points"],
        net_points=regions["net_points"],
        output_video_path=Path(args.output_video),
        output_json_path=Path(args.output_json),
        output_heatmap_path=Path(args.output_heatmap),
        show=args.show,
    )

    print("Analise concluida.")
    for k, v in metrics.items():
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
