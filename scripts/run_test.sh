#!/usr/bin/env bash
set -euo pipefail

# Uso rapido:
#   bash scripts/run_test.sh all
#   bash scripts/run_test.sh select
#   bash scripts/run_test.sh analyze
#
# Sobrescrever parametros por CLI (opcional):
#   bash scripts/run_test.sh all --video /caminho/video.mp4 --show

# =========================
# Parametros de teste
# =========================
PYTHON_BIN="python3"
ACTION="all"                       # select | analyze | all
VIDEO_PATH="examples/example.mp4"  # ex: /home/alisson/videos/partida.mp4
CONFIG_PATH="configs/default.yaml"
REGIONS_JSON="outputs/regions.json"
OUTPUT_VIDEO="outputs/analise_teste.mp4"
OUTPUT_JSON="outputs/metricas_teste.json"
OUTPUT_HEATMAP="outputs/heatmap_teste.png"
SHOW="false"                       # true | false
SKIP_DISPLAY_CHECK="false"         # true | false (apenas etapa select)

print_help() {
  cat <<'EOF'
Runner de testes do YoloTT

Uso:
  bash scripts/run_test.sh [select|analyze|all] [opcoes]

Opcoes:
  --video PATH              Caminho do video (obrigatorio)
  --config PATH             YAML de configuracao (padrao: configs/default.yaml)
  --regions-json PATH       JSON das regioes (padrao: outputs/regions.json)
  --output-video PATH       Video de saida (padrao: outputs/analise_teste.mp4)
  --output-json PATH        Metricas de saida (padrao: outputs/metricas_teste.json)
  --output-heatmap PATH     Heatmap de toques (padrao: outputs/heatmap_teste.png)
  --show                    Exibe janela durante analise
  --skip-display-check      Pula validacao de display na GUI de selecao
  -h, --help                Mostra esta ajuda

Exemplos:
  bash scripts/run_test.sh all --video /dados/jogo.mp4
  bash scripts/run_test.sh select --video /dados/jogo.mp4
  bash scripts/run_test.sh analyze --video /dados/jogo.mp4 --show
EOF
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    select|analyze|all)
      ACTION="$1"
      shift
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
  esac
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --video)
      VIDEO_PATH="$2"
      shift 2
      ;;
    --config)
      CONFIG_PATH="$2"
      shift 2
      ;;
    --regions-json)
      REGIONS_JSON="$2"
      shift 2
      ;;
    --output-video)
      OUTPUT_VIDEO="$2"
      shift 2
      ;;
    --output-json)
      OUTPUT_JSON="$2"
      shift 2
      ;;
    --output-heatmap)
      OUTPUT_HEATMAP="$2"
      shift 2
      ;;
    --show)
      SHOW="true"
      shift
      ;;
    --skip-display-check)
      SKIP_DISPLAY_CHECK="true"
      shift
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "Erro: opcao desconhecida: $1"
      print_help
      exit 1
      ;;
  esac
done

if [[ -z "$VIDEO_PATH" ]]; then
  echo "Erro: informe --video /caminho/video.mp4"
  print_help
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

mkdir -p "$(dirname "$REGIONS_JSON")" "$(dirname "$OUTPUT_VIDEO")" "$(dirname "$OUTPUT_JSON")" "$(dirname "$OUTPUT_HEATMAP")"

run_select() {
  local cmd=("$PYTHON_BIN" src/select_regions_gui.py --video "$VIDEO_PATH" --output-json "$REGIONS_JSON")
  if [[ "$SKIP_DISPLAY_CHECK" == "true" ]]; then
    cmd+=(--skip-display-check)
  fi

  echo "[YoloTT] Selecionando ROI + mesa + rede..."
  "${cmd[@]}"
}

run_analyze() {
  local cmd=("$PYTHON_BIN" src/main.py
    --video "$VIDEO_PATH"
    --config "$CONFIG_PATH"
    --regions-json "$REGIONS_JSON"
    --output-video "$OUTPUT_VIDEO"
    --output-json "$OUTPUT_JSON"
    --output-heatmap "$OUTPUT_HEATMAP"
  )

  if [[ "$SHOW" == "true" ]]; then
    cmd+=(--show)
  fi

  echo "[YoloTT] Rodando analise..."
  local start_ts end_ts elapsed
  start_ts="$(date +%s.%N)"
  "${cmd[@]}"
  end_ts="$(date +%s.%N)"
  elapsed="$(awk "BEGIN {printf \"%.2f\", ($end_ts - $start_ts)}")"

  echo "[YoloTT] Concluido."
  echo "- Tempo analise: ${elapsed}s"
  echo "- Video:   $OUTPUT_VIDEO"
  echo "- Metricas: $OUTPUT_JSON"
  echo "- Heatmap: $OUTPUT_HEATMAP"

  if [[ -f "$OUTPUT_JSON" ]]; then
    local detection_rate class_name class_id class_found
    detection_rate="$($PYTHON_BIN -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d.get("ball_detection_rate", 0.0))' "$OUTPUT_JSON" 2>/dev/null || echo "")"
    class_name="$($PYTHON_BIN -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d.get("ball_class_name", ""))' "$OUTPUT_JSON" 2>/dev/null || echo "")"
    class_id="$($PYTHON_BIN -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d.get("ball_class_id", "None"))' "$OUTPUT_JSON" 2>/dev/null || echo "")"
    class_found="$($PYTHON_BIN -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); print(d.get("ball_class_found_in_model", False))' "$OUTPUT_JSON" 2>/dev/null || echo "")"

    if [[ -n "$detection_rate" ]]; then
      echo "- Taxa deteccao bola: $detection_rate"
      echo "- Classe da bola configurada: $class_name (id=$class_id, encontrada_no_modelo=$class_found)"
      if awk "BEGIN {exit !($detection_rate <= 0.0001)}"; then
        echo "[AVISO] Taxa de deteccao da bola ficou zerada."
        echo "[AVISO] Revise: ROI, pesos em model.path e analysis.ball_class_name no YAML."
      fi
    fi
  fi
}

case "$ACTION" in
  select)
    run_select
    ;;
  analyze)
    run_analyze
    ;;
  all)
    run_select
    run_analyze
    ;;
  *)
    echo "Erro: ACTION invalida: $ACTION"
    exit 1
    ;;
esac
