# research/ — DiagramInject & AdaptShield

Code cho Research Track của curriculum: [Research Track note](../../AI-Engineer-30Day-Curriculum/Research%20Track%20-%20Visual%20Prompt%20Injection%20%26%20Adaptive%20Defense/Research%20Track%20-%20Visual%20Prompt%20Injection%20%26%20Adaptive%20Defense.md)

Mục tiêu: đo khả năng sống sót của prompt injection nhúng trong ảnh sơ đồ kỹ thuật qua các phép biến đổi ảnh, và học một chính sách tiền xử lý thích ứng.

## Cấu trúc dự kiến

```
research/
├── diagram_gen/        # spec JSON → Graphviz → PNG (+ ground truth)
├── payloads/           # P1..P5 — nhúng payload ở 5 tầng ảnh
├── transforms/         # T0..T9 — JPEG, downsample, blur, quantize, DCT, OCR-sanitize
├── eval/               # constrained output schema + score(pred, gold) -> F1, ASR
├── policy/             # random / best-fixed / UCB / LinUCB / Thompson / oracle
├── runner/             # CLI chạy thí nghiệm, ghi log JSONL
├── data/
│   ├── synthetic/      # sinh tự động, có ground truth chính xác
│   └── heldout_real/   # ~50 sơ đồ thật (vẽ tay, screenshot draw.io)
└── results/            # bảng tiền tính toán (image, action) → (ASR, TF, latency)
```

## Nguyên tắc

- **Mọi thí nghiệm ghi 1 dòng JSONL**: `{run_id, image_id, payload_class, defense_id, asr_hit, tf_score, latency_ms, seed, model, model_version}`
- **Deterministic**: `temperature=0`, seed cố định ở mọi bước sinh ảnh và inference. Không tái lập được = kết quả vô giá trị.
- **Chấm điểm không dùng LLM-judge**: ép VLM trả JSON đúng schema bằng `outlines`, so khớp tập hợp với ground truth.
- **Luôn báo cáo cặp (ASR, TF)**, không bao giờ báo ASR một mình.
- **Tiền tính toán bảng `(image, action)` một lần**, học policy offline từ bảng đó.

## Phạm vi đạo đức

Chỉ tấn công model local do chính mình chạy và API tự trả tiền. Sơ đồ trong benchmark là hư cấu, sinh tự động — không dùng tài liệu kiến trúc thật của bất kỳ tổ chức nào.

## Trạng thái

Chưa bắt đầu. Việc đầu tiên: `diagram_gen/` + payload P1, P4 + `eval/` (xem Pha 0 trong Paper Plan).
