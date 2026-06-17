# YoloTT

Projeto em Python para analise de partidas de tenis de mesa por video usando YOLO (Ultralytics) e OpenCV.

## O que este projeto faz

- Detecta e rastreia apenas a bola dentro da ROI selecionada.
- Gera video anotado com ROI, caixa da bola e rastro da bola.
- Calcula metricas basicas:
  - taxa de deteccao da bola,
  - velocidade media e maxima da bola (em pixels/segundo),
  - estimativa de ralis.
- Exporta as metricas em JSON.

## Estrutura

- `src/main.py`: CLI principal.
- `src/analyzer.py`: pipeline de deteccao, render e metricas.
- `src/prepare_openttgames_yolo.py`: converte OpenTTGames para formato YOLO da bolinha.
- `src/train_ball_yolo.py`: fine-tuning do YOLO para bolinha.
- `src/config.py`: carga do YAML de configuracao.
- `scripts/download_openttgames.sh`: download e extracao do OpenTTGames.
- `configs/default.yaml`: parametros de modelo e analise.
- `outputs/`: artefatos de saida (video e JSON).

## Requisitos

- Python 3.10+
- Dependencias base em `requirements.txt`
- Dependencias CPU-only em `requirements-cpu.txt`

## Instalacao

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-cpu.txt
```

Instalacao alternativa (GPU/CUDA):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

1) Selecione apenas a ROI com GUI (maquina com display):

```bash
python src/select_regions_gui.py \
  --video /caminho/para/partida.mp4 \
  --output-json outputs/regions.json
```

Se aparecer erro de Qt/xcb/wayland, esse ambiente nao possui display funcional para GUI.
Nesse caso, rode essa etapa em uma maquina desktop com interface grafica, leve o arquivo
`outputs/regions.json` para o servidor e execute somente a etapa 2 no servidor.

2) Rode a analise sem GUI (pode ser em servidor/headless):

```bash
python src/main.py \
  --video /caminho/para/partida.mp4 \
  --regions-json outputs/regions.json
```

Com janela de visualizacao em tempo real:

```bash
python src/main.py --video /caminho/para/partida.mp4 --show
```

Definindo arquivos de saida:

```bash
python src/main.py \
  --video /caminho/para/partida.mp4 \
  --regions-json outputs/regions.json \
  --output-video outputs/minha_analise.mp4 \
  --output-json outputs/minhas_metricas.json
```

## Fine-tuning com OpenTTGames

1) Baixe o dataset (modo rapido com `game_1` + `test_2`):

```bash
bash scripts/download_openttgames.sh quick
```

Para baixar tudo (muitos GB):

```bash
bash scripts/download_openttgames.sh full
```

2) Converta para YOLO (classe unica `ball`):

```bash
python src/prepare_openttgames_yolo.py \
  --dataset-root datasets/OpenTTGames \
  --output-dir datasets/OpenTTGames/yolo_ball \
  --bbox-size 14 \
  --frame-step 2
```

3) Rode o fine-tuning:

```bash
python src/train_ball_yolo.py \
  --data datasets/OpenTTGames/yolo_ball/dataset.yaml \
  --model yolov8n.pt \
  --epochs 12 \
  --imgsz 960 \
  --batch 8 \
  --device cpu
```

Ao final, o melhor peso fica em `outputs/weights/yolo_ball_openttgames.pt`.

4) Use o novo peso na analise:

Edite `configs/default.yaml` em `model.path` para `outputs/weights/yolo_ball_openttgames.pt`.

## Observacoes importantes

- O modelo padrao (`yolov8n.pt`) e geral e pode nao detectar bola de tenis de mesa com alta confianca em todos os cenarios.
- Para melhor desempenho em tenis de mesa real, o ideal e treinar/fine-tunar um modelo com dataset especifico (bola pequena, alta velocidade, angulos variados).
- As metricas sao estimativas iniciais para baseline de analise e consideram apenas o rastreamento da bola.
- O JSON de metricas inclui `estimated_rebounds` e `rebound_timestamps_seconds` (rebatidas estimadas pela mudanca de direcao da trajetoria da bola).

## Proximos passos sugeridos

- Calibrar a area da mesa por homografia para converter pixels em metros.
- Adicionar rastreamento multiobjeto mais robusto (ByteTrack/BoT-SORT).
- Estimar eventos de saque, quique e troca de posse por lado da mesa.
