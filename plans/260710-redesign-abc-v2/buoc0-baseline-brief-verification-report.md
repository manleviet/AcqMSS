# Bước-0 report — baseline + đối chiếu brief ↔ main

Date: 2026-07-10 · Branch created: `feat/redesign-abc-v2` (từ `main` @ `c7d40a0`)
Brief source (Cowork-owned, KHÔNG sửa): `<vault>/Cowork/explanation/redesign-abc-task-plan.md` (2026-06-28)

## 1. Baseline (hợp đồng hành vi)

| Branch | Kết quả | Ghi chú |
|---|---|---|
| `main` (c7d40a0) | **344 passed**, 2 warnings, 50.7s | warnings: PytestCollectionWarning `TestSuiteReader`; unregistered mark `slow` |
| `feat/redesign-abc` (tip 35d6cb3) | **593 passed**, 55.7s | đích đối chiếu: v2 phải ≥ 593 |

Lệnh: `PYTHONPATH=. uv run --no-sync pytest tests/ -q`

## 2. Claims brief VERIFIED ✅ trên main (mẫu chính)

- `task_preparation.py`: TaskInput:38, DiagnosisTask:88, TestCaseTask:112, `_assign_sets` ×2 explanation (390, 525) + ConGenTask (acqmss/task_preparation.py:30), QuAcqTask (quacq/task_preparation.py:27); `_ASSUMPTION_PAIR_STRIDE` rò vào đúng 3 file conacq (fm_oracle_model, acqmss/task_preparation, quacq/task_preparation).
- `profiler.py` = 1220 LOC monolith. `performance_metrics.py` = 652 LOC, `_stat4` = 25 hit.
- `print(` apps = 254 (khớp brief).
- `VariableCodec` = 0 hit trên main (khớp: main không có codec).
- 4 bản encoding rải: `fm_oracle._model_to_config:149`, `fm_oracle_model._config_to_assumptions:108`, `quacq_model.config_to_assumptions:116` + `model_to_config:174`, `data_structures.to_literals:81`.
- #4 verified: `fm_oracle_model._base_set_c:47`, `with_configuration:121` mutate `task.set_c:130`, fold `_base_set_c:234-240`. KHÔNG có field `task.base_set_c` trên main — đúng brief (artifact thời tip).
- Oracle ABC stub: `base.py` — `get_variables:38`, `complete_configuration:41` (stub), `is_valid` abstract.
- Shims tồn tại: `CheckerModel` Protocol (checker.py:23), `create_from_model` (checker.py:269). **`create_from_task` CHƯA có trên main.**
- sat4j clones: `pysat_conflict_sat4j.py`, `pysat_diagnosis_sat4j.py` tồn tại.
- FastDiagP tự ôm: `lookup_table:42`, `mp.Pool:76`.
- `next_available_id` baton: 14 file (conacq 10 + explanation 4).
- `#1` verified: `_bg_data` lazy + `RuntimeError("Call prepare() first")` (fm_oracle_model:51,59,66,73). `#10` verified: `complete_configuration` dựng `Solver()` mỗi call (fm_oracle.py:116,134).
- `dimacs_to_configuration.py` tồn tại trên main (T17 GIỮ). `test_diagnosis.py` = 1328 LOC. `tests/conftest.py`+`resource_paths.py` CHƯA có. `test_bias_module.py`+`test_bias_module_1.py` tồn tại (demo). Checker: Incremental/NonIncremental/SAT4J + Factory. Labeler 5 file. `result_loader` ở `conacq/eval/`.
- pyproject packages hiện tại: `conacq*`, `explanation*`, `apps*` → T8 phải thêm `profiling*`.

## 3. LỖI CƠ HỌC brief ↔ main (Cowork đồng bộ vào brief; KHÔNG phải bất đồng design)

1. **T16 file list**: brief ghi RNG ở `base/feature_frequency/nwise_coverage/random_sampling`. Thực tế `nwise_coverage.py` KHÔNG dùng `random`; file thứ 4 dùng RNG global là **`query_provider.py:56`** (`random.shuffle(self._pool)`).
2. **T9 "File chính"**: `conacq/runners/base_runner.py` **ĐÃ TỒN TẠI trên main** (modify, không phải create-new).
3. **Đếm print**: brief "13 conacq + 22 explanation"; grep thô = 20 conacq + 31 explanation (chênh do docstring/comment prints — xác định lại khi làm T10; apps 254 khớp).
4. **Import profiler**: brief "~34+ site"; đo được **26 dòng import / 26 file**.
5. **Import sâu conacq→explanation (T12)**: brief "~24 site"; đo được **47 dòng** `from explanation.*` (không qua api). Đều rewrite hết ở T12, số lớn hơn chỉ ảnh hưởng effort.
6. **T0 WHY**: brief "3 file unittest rời"; thực tế 2 file dùng unittest (`test_diagnosis.py`, `test_utils.py`) + 2 file demo `test_bias_module*`.
7. **README main drift** (không thuộc brief nhưng liên quan): README Quick-Start minh hoạ `model.prepare_task(TaskInput(...), oracle)` + `CheckerFactory.create_from_task(...)` — cả hai **chưa tồn tại trên main**. API này trùng đích v2 → tự khớp khi T3/T11 xong; không cần hành động, ghi để T18 soát.

## 4. Bất đồng DESIGN

**Không có.** Mọi quyết định #1–#10, Task-family, encoding/KB, oracle, boundary, sequencing đều khớp với hiện trạng main sau verify.

## Unresolved questions

- Không có câu hỏi chặn. Mục 3 chỉ cần Cowork đồng bộ brief (không đổi quyết định nào).
