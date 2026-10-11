# ArchAgent

Local-first DevOps System Architect Agent. Đọc docs/kiến trúc hệ thống, research qua RAG, đề xuất System Design theo format **Vấn đề → Giải pháp → Drawback → Research**, và kiểm chứng đề xuất bằng function calling trước khi trả lời.

Xây dựng theo lộ trình 30 ngày tại [`../AI-Engineer-30Day-Curriculum/`](../AI-Engineer-30Day-Curriculum/AI-Engineer-30Day-Curriculum.md).

## Cấu trúc module (theo tuần)

| Module | Tuần | Mô tả |
|---|---|---|
| `security/` | 1 | Injection test log, latency benchmark của guardrail |
| `safety_wrapper/` | 1 | Middleware chặn input/output độc hại (Sprint 1) |
| `rag/` | 2 | So sánh chunking, hybrid search |
| `knowledge_base/` | 2 | Pipeline ingest + query đầy đủ (Sprint 2) |
| `local_models/` | 3 | Benchmark HF models, function calling với Ollama |
| `reasoning_engine/` | 3 | Agentic loop (ReAct) chạy local (Sprint 3) |
| `multimodal_reviewer/` | 4 | Vision/Audio input + tích hợp toàn bộ pipeline (Sprint 4) |
| `performance/` | 4 | Cost/latency tracking |
| `data/sample_docs/` | — | Tài liệu mẫu dùng để test retrieval |
| `blog/` | — | `week_N_solution_story.md` — case study mỗi tuần |
| `tests/` | — | Test cho từng module |

## Setup — Conda env

**Python 3.11** — lựa chọn ổn định nhất cho stack này (không phải bản mới nhất). Lý do:

| Package | Ràng buộc Python | Ghi chú |
|---|---|---|
| `torch` (dependency của `sentence-transformers`, `transformers`) | wheel chính thức cho 3.11/3.12/3.13 từ PyTorch 2.6 | 3.13 mới có wheel ổn định gần đây, ít giờ bay production hơn |
| `faiss-cpu` | wheel PyPI cho 3.13 **chưa đầy đủ/ổn định** trên Windows; repo build wheel chính (`faiss-wheels`) đã bị archive (06/2026) | Rủi ro cao nhất trong stack — lý do chính không chọn 3.13/3.14 |
| `llama-index` | yêu cầu `>=3.9,<4.0` | Không giới hạn thêm |
| `outlines` (constrained decoding cho Ollama, Day 17-18) | core yêu cầu `>=3.8` | Không giới hạn thêm |

→ **3.11** có coverage wheel rộng nhất trên Windows cho toàn bộ stack (đặc biệt `faiss-cpu`), đã qua nhiều năm ổn định. 3.12 là lựa chọn thay thế chấp nhận được nếu cần feature mới hơn của Python. Tránh 3.13/3.14 cho tới khi `faiss-cpu` có wheel Windows xác nhận ổn định.

```bash
conda create -n archagent python=3.11 -y
conda activate archagent
pip install -r requirements.txt
```

Hoặc dùng file khai báo sẵn:

```bash
conda env create -f environment.yml
conda activate archagent
```

Copy `.env.example` thành `.env` và điền API key (nếu dùng cloud fallback). Cài [Ollama](https://ollama.com) cho phần local model (Tuần 3).

## Trạng thái

Skeleton — chưa có logic. Bắt đầu implement theo thứ tự Day 01 → Day 30 trong curriculum.
