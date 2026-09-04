# DiagnosisModel / `task_input` — Phân tích thiết kế & rủi ro tái dùng model

> **Bối cảnh:** Tổng hợp phiên hỏi-đáp kiến trúc (2026-06-17) về cách `task_input` được dùng trong `DiagnosisModel` và các họ model liên quan (`ConGenModel`, `FMOracleModel`). Dành cho cowork đọc nhanh — không cần đọc lại toàn bộ chat.
>
> **Phạm vi file:** `explanation/models/pysat_diagnosis_model.py`, `explanation/models/task_preparation.py`, `explanation/models/diagnosis_model_builder.py`, `conacq/algorithms/acqmss/congen_model.py`, `conacq/algorithms/acqmss/task_preparation.py`, `conacq/oracle/fm_oracle_model.py`.
>
> **Tính chất:** Tư vấn/phân tích (advisory). Chưa sửa code nào.

---

## TL;DR

1. **`task_input` lấy thẳng từ model, không qua hai hàm private** — vì strategy nhận cả `model` (duck-typed) làm single source of truth; tham số `task_input` của `_prepare_diagnosis_task`/`_prepare_testcase_task` là **dead parameter** (di tích refactor `57ada8e`).
2. **3 chế độ tái dùng model + 1 chế độ đảo ngược** — bất biến chung: re-prepare phải vô hiệu hóa artifact dẫn xuất (`_task`, `checker`). Hiện được giữ **bằng quy ước**, không enforce.
3. **`next_available_id` KHÔNG bao giờ reset vì KHÔNG bao giờ đổi** — nó là hằng số (ranh giới var SAT ↔ assumption literal). Mỗi `prepare()` đọc lại từ cùng mốc → ID re-derive xác định.

---

## Q1. Vì sao `task_input` lấy trực tiếp từ model, không "đi qua" `_prepare_diagnosis_task` / `_prepare_testcase_task`?

### Quan sát
`pysat_diagnosis_model.py:256-286` — hai hàm private nhận tham số `task_input` nhưng **không dùng**, chỉ truyền `self`:

```python
def _prepare_diagnosis_task(self, task_input: TaskInput) -> DiagnosisTask:
    strategy = TaskPreparationFactory.create_diagnosis(self.use_incremental)
    output = strategy.prepare(self)        # truyền self, KHÔNG truyền task_input
```

Strategy đọc thẳng từ model (`task_preparation.py:362`):
```python
def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
    task_input = model.task_input          # ← lấy trực tiếp từ model
```

### Lý do thiết kế
1. **Strategy cần nhiều hơn `task_input`** — còn cần `constraint_map`, `negated_constraint_map`, `variables`, `next_available_id` (`task_preparation.py:362-382`), tất cả đều ở model → gom về **một contract `model`** (KISS/DRY).
2. **Duck-typing để tái dùng strategy** — docstring `task_preparation.py:209-210` khai báo `model: Any` với interface `constraint_map / negated_constraint_map / variables / task_input / next_available_id`. Nhờ vậy `ConGenModel` và `FMOracleModel` tái dùng đúng cơ chế (xác nhận: `congen_model.py:229-238`).
3. **`prepare()` đã set `self._task_input` trước khi rẽ nhánh** (`pysat_diagnosis_model.py:244-254`) → tham số truyền vào hai hàm private là **thừa**, chỉ còn dùng để chọn nhánh ở `prepare()`.

### Đánh giá
Tham số `task_input` ở hai hàm private là **dead parameter** từ commit `57ada8e`. Không sai logic (model giữ đúng `task_input`) nhưng gây hiểu nhầm.

**Khuyến nghị (YAGNI):** Bỏ tham số `task_input` khỏi `_prepare_diagnosis_task`/`_prepare_testcase_task` → `_prepare_*_task(self)`. Sửa ~4 dòng + docstring, không rủi ro.

---

## Q2. Các tình huống tái dùng model nhưng `task_input` đổi

### Vòng đời state → derived
```
task_input ──prepare()──► _task (set_c/set_b/set_kb/assumptions) ──create_checker()──► checker
   (state)                 (derived #1)                              (derived #2: snapshot KB)
```
`checker` chụp `get_kb()` + `get_assumptions()` lúc tạo → điểm dễ vỡ nhất.

### Scenario A — ConGen Cross-Validation folds *(reuse có chủ đích, an toàn)*
- `congen_runner.py:153` / `congen_model_builder.py:38` → cùng `ConGenModel`, mỗi fold `model.prepare(oracle, positive_examples=…, negative_examples=…)`.
- `congen_model.py:229` thay **nguyên khối** `TaskInput`, rebuild `_task` + `set_neg_tv` + provider (`:241-243`).
- An toàn vì prepare() idempotent (drop `_task` cũ) + checker tạo trong operation và `cleanup()` ở `finally` (`pysat_redundancy_testcases.py:66-67`).

### Scenario B — FMOracleModel membership queries *(hot path, đảo ngược bất biến)*
- `prepare(configuration=…)` (`fm_oracle_model.py:168`) — re-prep đầy đủ.
- **`with_configuration(configuration)` (`:130`)** — HOT PATH: chỉ
  ```python
  self.task.set_c = self._base_set_c + self._config_to_assumptions(configuration)
  ```
  **Không** đụng `set_kb`/`assumptions`, **không** cập nhật `task_input`.
- → Đây là chiều ngược: input đổi mỗi query nhưng `task_input` **đứng yên, lệch pha** với `task`. Cố ý (perf: build KB một lần). **Hazard nhất quán** nếu code đọc `model.task_input` để suy trạng thái hiện tại.

### Scenario C — DiagnosisModel đổi loại task giữa chừng *(reuse hợp lệ, rủi ro checker stale)*
- Cùng model, `prepare(new_task_input)` chuyển loại task (`pysat_diagnosis_model.py:244-254`).
- Docstring cảnh báo (`:240-242`): *"any existing checker instances must be recreated as they hold references to the previous KB/assumptions."*
- Hiện chưa nổ vì checker luôn tạo trong `execute()` rồi huỷ — **quy ước, không enforce**. Nếu caller cache checker xuyên prepare() → SAT sai âm thầm.

### Bảng rủi ro
| # | Tình huống | task_input đổi? | Cần invalidate | Bảo vệ bởi | Rủi ro |
|---|-----------|-----------------|----------------|------------|--------|
| A | ConGen folds | Thay nguyên khối | `_task`, checker | rebuild + checker per-op | Thấp |
| B | FMOracle `with_configuration` | **Không** (chỉ set_c) | — (KB giữ cố ý) | thiết kế hot-path | TB (task_input lệch task) |
| C | DiagnosisModel đổi task type | Thay nguyên khối | `_task`, **checker** | chỉ *quy ước* | TB–cao nếu cache checker |
| — | Giữ `_task` cũ rồi trộn ID | — | reference cũ | Không có | Cao nếu vi phạm |

**Nguyên nhân gốc:** model stateful + re-preparable, nhưng invalidate state dẫn xuất **không enforce** (thiếu dirty-flag / generation counter).

### Khuyến nghị
1. **Generation counter** — `self._generation` tăng mỗi `prepare()`; checker assert generation khớp → biến lỗi âm thầm thành lỗi ồn ào (~10 dòng). Làm trước nếu định cache checker.
2. **Đồng bộ task_input ở hot path** — `with_configuration` nên cập nhật `task_input.configuration` hoặc tài liệu hoá rõ `task` mới là nguồn chuẩn.
3. **Không tách `task_input` ra ngoài model** — vì checker cũng phụ thuộc `_task` trên model; giữ tất cả trên một object cho phép một generation counter bảo vệ toàn chuỗi.

---

## Q3. `next_available_id` có reset sau mỗi fold không?

### Trả lời: **Không cần reset — vì không bao giờ bị đổi (immutable).**

`task_preparation.py:97` (ConGen) — mỗi `prepare()` chỉ **đọc** vào biến cục bộ:
```python
id_assumption = model.next_available_id   # copy, không phải reference
```
Mọi cấp ID tăng `id_assumption` cục bộ, không write-back. Comment chốt ý đồ (`task_preparation.py:116-118`):
```python
# NOTE: Do NOT update model.next_available_id here.
# model.next_available_id was set by the builder at build time and should remain fixed.
# Updating it here would cause subsequent prepare() calls to allocate IDs from wrong range.
```
`explanation/models/task_preparation.py:368, 504` cùng pattern, không write-back.

### Hệ quả cho CV folds
`next_available_id` = ranh giới cố định giữa **biến SAT thật** (feature vars + Tseitin) và **assumption literals**. Mỗi fold bắt đầu cấp assumption từ **cùng mốc** → ID **re-derive xác định, bị tái dùng giống hệt** giữa các fold:
```
Fold 1: id bắt đầu = next_available_id (vd 1000) → bias=1000.., E+=10xx.., NE=10yy..
Fold 2: id bắt đầu = next_available_id (vẫn 1000) → bias=1000.. (TRÙNG), ...
```
An toàn **chỉ vì** `_task` fold cũ bị drop (`congen_model.py:241`) + checker huỷ per-op → hai `_task` không bao giờ cùng sống trong một solver.

**Nếu write-back** `next_available_id += …` → fold sau cấp ID từ dải sai → đè biến Tseitin/feature thật → corruption. Comment `:118` chính là để chặn bẫy đó.

### Khi nào thành bug
Chỉ khi **giữ reference `_task` fold cũ** rồi trộn assumptions với fold mới trong cùng lời gọi solver. Hiện không caller nào làm vậy.

---

## Trích dẫn nguồn (path:line)
- `explanation/models/pysat_diagnosis_model.py:244-286` — `prepare()` + hai hàm private (dead param).
- `explanation/models/task_preparation.py:209-210, 362-382` — duck-typed strategy contract.
- `explanation/models/task_preparation.py:368, 504` — đọc `next_available_id`, không write-back.
- `explanation/models/diagnosis_model_builder.py:312-324` — builder set `task_input` rồi `prepare()`.
- `conacq/algorithms/acqmss/congen_model.py:225-245` — re-prepare per fold.
- `conacq/algorithms/acqmss/task_preparation.py:97, 116-118` — `next_available_id` immutable + comment cảnh báo.
- `conacq/oracle/fm_oracle_model.py:130, 168` — hot path `with_configuration` vs full `prepare`.
- `explanation/operations/pysat_redundancy_testcases.py:56-67` — checker tạo trong execute() + cleanup finally.

## Câu hỏi chưa giải quyết
1. Có kế hoạch **cache/giữ checker xuyên nhiều `prepare()`** không? → quyết định Generation counter có cần thiết hay vẫn YAGNI.
2. Ngoài `FMOracleModel.with_configuration`, còn caller nào đọc `model.task_input` **sau** hot-path mutation để suy trạng thái không? → nếu có, Scenario B thành bug thật.
