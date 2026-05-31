# Dataset setup (not committed to Git)

Per submission guidelines, **raw CCTV and normalized `dataset/` are excluded from Git** (size + challenge rules).

## Required layout on evaluator machine

```
purplle/
├── CCTV Footage/
│   ├── CAM 1.mp4 … CAM 5.mp4
└── dataset/
    ├── store_layout.json
    ├── pos_transactions.csv
    ├── sample_events.jsonl
    └── generated_events.jsonl   # optional; pipeline creates if missing
```

## Bootstrap commands

```bash
python scripts/prepare_dataset.py
```

This normalizes POS CSV → `dataset/pos_transactions.csv` and refreshes `sample_events.jsonl`.

## Full pipeline (generates events)

```bash
cd store-intelligence
export VIDEO_DIR=../CCTV\ Footage   # or ../dataset/videos
export MAX_FRAMES_PER_VIDEO=120
python pipeline/run_pipeline.py
```

Output: `dataset/generated_events.jsonl`
