from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

import cv2

BBox = Tuple[int, int, int, int]
Point = Tuple[int, int]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Selecao GUI de ROI, mesa e rede para analise")
    parser.add_argument("--video", required=True, help="Caminho para o video de entrada")
    parser.add_argument(
        "--output-json",
        default="outputs/regions.json",
        help="Caminho do JSON com ROI, pontos da mesa e pontos da rede",
    )
    parser.add_argument(
        "--skip-display-check",
        action="store_true",
        help="Pula validacao previa de display (use apenas se tiver certeza que a GUI funciona)",
    )
    return parser


def _has_qt_wayland_plugin() -> bool:
    plugin_dir = Path(cv2.__file__).resolve().parent / "qt" / "plugins" / "platforms"
    if not plugin_dir.exists():
        return False

    for item in plugin_dir.iterdir():
        if "wayland" in item.name.lower():
            return True
    return False


def check_display_support() -> Tuple[bool, Optional[str]]:
    if os.name == "nt":
        return True, None

    display = os.environ.get("DISPLAY")
    wayland = os.environ.get("WAYLAND_DISPLAY")
    if not display and not wayland:
        return False, "Nenhum display encontrado (DISPLAY/WAYLAND_DISPLAY ausentes)."

    # OpenCV + Qt no Linux frequentemente usa backend xcb.
    # Em sessao Wayland pura, sem DISPLAY/XWayland, selectROI tende a abortar.
    if wayland and not display and not _has_qt_wayland_plugin():
        return (
            False,
            "Sessao Wayland detectada, mas o OpenCV instalado nao possui plugin Qt Wayland e tambem nao ha DISPLAY para xcb.",
        )

    # Em Linux, DISPLAY pode existir e ainda assim estar inacessivel.
    if display and shutil.which("xdpyinfo"):
        probe = subprocess.run(["xdpyinfo"], capture_output=True, text=True, check=False)
        if probe.returncode != 0:
            return False, "DISPLAY definido, mas inacessivel para aplicacoes X11 (xdpyinfo falhou)."

    return True, None


def select_single_region(frame, window_name: str) -> BBox:
    x, y, w, h = cv2.selectROI(window_name, frame, showCrosshair=True, fromCenter=False)
    cv2.destroyWindow(window_name)
    if w <= 1 or h <= 1:
        raise RuntimeError("Selecao invalida. Delimite uma area maior que 1x1.")
    return (int(x), int(y), int(x + w), int(y + h))


def clip_bbox_to_frame(bbox: BBox, width: int, height: int) -> BBox:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))
    return (x1, y1, x2, y2)


def bbox_to_list(bbox: BBox) -> List[int]:
    return [bbox[0], bbox[1], bbox[2], bbox[3]]


def points_to_list(points: List[Point]) -> List[List[int]]:
    return [[int(x), int(y)] for x, y in points]


def _draw_point_selection(frame, points: List[Point], title: str, instruction: str):
    canvas = frame.copy()

    for idx, (x, y) in enumerate(points, start=1):
        cv2.circle(canvas, (x, y), 6, (0, 255, 255), -1)
        cv2.putText(
            canvas,
            str(idx),
            (x + 8, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        canvas,
        title,
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        instruction,
        (12, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return canvas


def select_four_points(frame, window_name: str, title: str) -> List[Point]:
    points: List[Point] = []

    def on_mouse(event, x, y, flags, param):
        del flags, param
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((int(x), int(y)))

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, on_mouse)

    instruction = "Clique 4 pontos. ENTER confirma, R reinicia, ESC cancela."
    while True:
        canvas = _draw_point_selection(frame, points, title, instruction)
        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(20) & 0xFF

        if key == 27:  # ESC
            cv2.destroyWindow(window_name)
            raise RuntimeError("Selecao cancelada pelo usuario.")
        if key in (ord("r"), ord("R")):
            points.clear()
        if key in (13, 10):  # ENTER
            if len(points) == 4:
                break

    cv2.destroyWindow(window_name)
    return points


def run(video_path: Path, output_json_path: Path) -> Dict[str, object]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Nao foi possivel abrir o video: {video_path}")

    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Nao foi possivel ler o primeiro frame do video: {video_path}")

    h, w = frame.shape[:2]

    roi_bbox = select_single_region(
        frame,
        "YoloTT - Selecione a regiao de interesse e pressione ENTER",
    )

    table_points = select_four_points(
        frame,
        "YoloTT - Pontos da Mesa",
        "Selecione os 4 cantos da mesa (ordem livre)",
    )

    net_points = select_four_points(
        frame,
        "YoloTT - Pontos da Rede",
        "Selecione 4 pontos sobre a rede (ordem livre)",
    )

    cv2.destroyAllWindows()

    roi_bbox = clip_bbox_to_frame(roi_bbox, w, h)

    data: Dict[str, object] = {
        "video": str(video_path),
        "frame_size": {"width": w, "height": h},
        "roi_bbox": bbox_to_list(roi_bbox),
        "table_points": points_to_list(table_points),
        "net_points": points_to_list(net_points),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.skip_display_check:
        ok, reason = check_display_support()
        if not ok:
            raise RuntimeError(
                "Nao foi encontrado display grafico funcional para GUI. "
                f"Motivo: {reason} "
                "Se voce estiver em Wayland, habilite XWayland para obter DISPLAY (xcb) ou use uma maquina com GUI compativel. "
                "Depois gere o JSON de regioes e rode src/main.py no servidor."
            )

    regions = run(Path(args.video), Path(args.output_json))

    print("Selecao concluida.")
    print(f"- roi_bbox: {regions['roi_bbox']}")
    print(f"- table_points: {regions['table_points']}")
    print(f"- net_points: {regions['net_points']}")
    print(f"- output_json: {args.output_json}")


if __name__ == "__main__":
    main()
