# Implementation Plan — redesign A+B+C v2

- **Design source (WHAT/WHY — Cowork sở hữu, KHÔNG quyết lại):** `<vault>/Cowork/explanation/redesign-abc-task-plan.md` + `redesign-abc-reapply-plan.md` (tham khảo commit-map). Plan này chỉ là **HOW**, neo vào main.
- **Branch:** `feat/redesign-abc-v2` (từ `main` c7d40a0). Baseline: main **344 passed** · tip `feat/redesign-abc` 35d6cb3 **593 passed** (đích ≥).
- **Đối chiếu Bước-0:** `buoc0-baseline-brief-verification-report.md` (cùng thư mục) — 0 bất đồng design, 7 lỗi cơ học đã ghi.
- **Thứ tự thi công:** T0 → T1 → T2 → T8 → T3 → T12 → T5 → T6 → T7 → T9 → T10 → T11 → T13 → T14 → T15 → T16 → T17 → **T4 (cuối)** → T18.

## Khung chung MỖI task (lặp lại, không ghi lại từng task)

1. **Đọc 3 chiều:** `git show main:<file>` (hành vi gốc) · `git show feat/redesign-abc:<file>` (tham khảo phần tốt) · brief (target). Edit cụ thể re-derive trên main.
2. **Safety-net trước** nếu module chưa có test (ghi rõ ở task nào bên dưới).
3. Implement → `PYTHONPATH=. pytest tests/ -v` **XANH** (không làm yếu assertion).
4. **Docs in-stage:** task đổi API/cấu trúc → cập nhật `docs/system-architecture.md` / `docs/codebase-summary.md` / docstrings NGAY.
5. Commit conventional (không AI ref) → **DỪNG, tóm tắt cho user duyệt** → mới sang task kế.
6. Ngoài brief → ghi report + HỎI. Bất đồng design → DỪNG, hỏi Cowork.

---

## T0 — Nền pytest (additive)

Main: KHÔNG có `tests/conftest.py`/`tests/resource_paths.py`; resource path hardcode rải; 2 file unittest-style (`test_diagnosis.py`, `test_utils.py` — giữ nguyên style ở T0).

1. Viết `tests/resource_paths.py`: hằng/helper đường dẫn (`data/fms/`, `data/bias/`, `data/testsuites/`…, `tests/resources/`) — tham khảo tip.
2. Viết `tests/conftest.py`: fixture dùng chung (paths); đăng ký marker `slow` (xoá warning unregistered-mark).
3. KHÔNG migrate ồ ạt test cũ — chỉ dựng nền; test cũ migrate dần trong task liên quan.

**Green:** 344 passed, collect đúng, warning `slow` biến mất.

## T1 — Task hierarchy frozen, pure data (additive)

Main anchors: `explanation/models/task_preparation.py` (TaskInput:38, DiagnosisTask:88, TestCaseTask:112, `_assign_sets`:390/525); `conacq/algorithms/acqmss/task_preparation.py:30` (ConGenTask), `conacq/algorithms/quacq/task_preparation.py:27` (QuAcqTask); mutate-site ngoài prep: `fm_oracle_model.with_configuration:130` (`task.set_c = …`).

1. Enumerate mutate-sites: `grep -rn "task\.set_\|result\.set_\|\.assumptions\s*=\|\.negation_map\s*=" conacq/ explanation/ tests/` — liệt kê đủ trước khi freeze.
2. `Task(ABC)` = `@dataclass(frozen=True)`: field solve nội tại `set_c/set_b/assumptions: List[int]`, `set_kb: List[List[int]]`, `negation_map: Dict[…]` (#6 — kiểu chính xác re-derive trên main). KHÔNG method/codec/describe.
3. `DiagnosisTask(Task)` = `pass` (marker; KHÔNG khai `base_set_c` — #4). `TestCaseTask` chỉ thêm field TC (đọc main cho đủ set_tc/set_tv/set_neg_tv/set_neg_tc). `ConGenTask(TestCaseTask)`, `QuAcqTask(DiagnosisTask)` + `constraint_clauses` — pure data.
4. `get_cf` → free function `cf(task) = task.set_b + task.set_c` (module task_preparation).
5. `TaskInput` = frozen + `__post_init__` validate tổ hợp loại trừ + factory classmethod (`fm_diagnosis()/config()/config_with_cf()/error()/testcases()/redundancy_fm()/redundancy_t()`). Field nội tại y nguyên.
6. Prep strategies → **build-then-freeze**: `_assign_sets` tính local rồi dựng task một lần cuối. `with_configuration` → `dataclasses.replace` (tạm; xoá hẳn ở T11.2).
7. Query helpers QuAcq (`get_constraint_vars`…) chưa đụng (chờ encoding T2).

**Green:** additive; + test mới pin frozen/factory (vd `tests/test_task_immutability.py`).

## T2 — Encoding module + KB một nguồn (additive)

Main: 4 bản encoding rải (Bước-0 §2); KHÔNG có codec — **KHÔNG tạo VariableCodec**.

1. `explanation/models/encoding.py` (mới) — free functions: `config_to_variable_literals(config, name_to_id)` · `variable_literals_to_config(lits, id_to_name)` · `config_to_assignment_assumptions(config, assignment_map)` · `get_constraint_vars(clauses, id_to_name)`.
2. `explanation/models/assignment_assumption_map.py` (mới) — `AssignmentAssumptionMap` frozen, sở hữu `pos/neg_assignment_to_assumption`.
3. KB Protocol (`explanation/models/kb_protocol.py` mới): `id_to_name/name_to_id/constraint_map/negated_constraint_map/next_available_id`. `DiagnosisModel` thoả bằng property alias (`id_to_name`→`features`, `name_to_id`→`variables` của PySATModel). Base `KBModel` (conacq, file mới) cho 3 model conacq đặt thẳng tên đó. Expose read-only qua `types.MappingProxyType`.
4. Migrate 4 bản encoding → gọi module `encoding` (fm_oracle:149, fm_oracle_model:108, quacq_model:116+174, data_structures:81). Query QuAcq → free function `(task, …)` đọc `constraint_clauses` + name↔id từ KB.
5. `constraint_map/negated_constraint_map` giữ prep-internal.

**Green:** additive; `tests/test_encoding.py` round-trip; 1 nguồn name↔id.

## T8 — profiling → package TOP-LEVEL (green-after-completion)

Main: `explanation/operations/algorithms/profiler.py` 1220 LOC; **26 dòng import** repo-wide; pyproject packages = `conacq*/explanation*/apps*`.

1. Tạo package **`profiling/` top-level** (ngang explanation/conacq): `protocol.py` (`ProfilerProtocol` @runtime_checkable [MỚI] + `AbstractProfiler` + `NullProfiler` + `MetricType` + `ProfilerError`) · `core.py` (concrete `Profiler`) · `decorators.py` · `presets.py` · `registry.py`. `__init__.py` facade giữ tên/API cũ.
2. **GIỮ** `ProfilerMode`/multiprocess nguyên trạng (T4 mới xoá).
3. Rewrite 26 import site → `from profiling import …`; xoá `profiler.py` cũ.
4. `pyproject.toml`: thêm `profiling*` vào packages.
5. Docs: codebase-summary (inventory profiler → profiling/), system-architecture (vị trí package).

**Green:** sau khi trọn task; `test_profiler.py` xanh; `isinstance(p, ProfilerProtocol)` đúng.

## T3 — Immutable KB + prepare_task→PreparedTask + execute(task) + sat4j seam (TỰ XANH, checkpoint lớn)

Main anchors: `pysat_diagnosis_model.py` state+getters (dòng 62–195: `_use_incremental/_task_input/_task/_description_provider`, `get_c/get_b/get_cf/get_kb/get_negation_map/get_assumptions/get_tc/get_tv/get_neg_tv/get_neg_tc`); shims `CheckerModel` (checker.py:23) + `create_from_model` (checker.py:269); sat4j clones 2 file; `congen_model.prepare:206` (gọi GenerateNE nội bộ).

1. `PreparedTask(task, describe, assignment_map)` — mở rộng/đổi tên `PreparationOutput` (`describe` = `description_provider` cũ, xoá trùng).
2. `DiagnosisModel` → KB immutable: xoá state/getters trên; name↔id qua alias (T2). `use_incremental` → tham số operation.
3. `prepare_task(task_input) -> PreparedTask` = entry duy nhất, pure, build-then-freeze. Xoá `model.prepare()`.
4. Ops `execute(task)` (đọc `task.set_c/set_b/…`): `pysat_abstract_explanation/pysat_conflict/pysat_diagnosis/…`; `DiagnosisFormatter` đọc `ctx.describe`.
5. `CheckerFactory.create_from_task(task, solver_name, use_incremental, profiler)`; **xoá** `create_from_model` + `CheckerModel`. Enumerate call-site: `grep -rn "create_from_model\|get_kb()\|get_assumptions()" conacq/ apps/ tests/` → chuyển task-based (conacq `prepare()` main-style vẫn trả Task → dùng được ngay; chữ ký conacq thống nhất ở T11).
6. `GenerateNE` pure (không mutate model).
7. **sat4j seam:** dựng seam SolverBackend tối thiểu; gộp sat4j vào `pysat_conflict`/`pysat_diagnosis` (backend param); **xoá 2 file** `pysat_*_sat4j.py`; formalize port ở T7.
8. `tests/test_diagnosis.py`: chỉ cập nhật lời-gọi-API (GIỮ monolith unittest đến T13).
9. **FastDiagP GIỮ NGUYÊN** main-style (pool/lookup_table nguyên) — chỉ ăn checker-từ-task. Executor rewrite = T4 cuối.

**Green:** TỰ XANH toàn suite. Docs: system-architecture (prepare_task/PreparedTask/execute(task)), codebase-summary.

## T12 — Public surface + boundary guard 2 chiều

Main: **47 dòng** `from explanation.*` trong conacq (không qua api); stride rò 3 file conacq.

1. `explanation/api.py` — mặt tiền curated: `TaskInput/Task/PreparedTask`/prepare-helpers/`TestSuite`…/`ConsistencyChecker`/`CheckerFactory`/`QuickXPlain`/utils/`FmToDiagPysat` + `encoding` + `AssignmentAssumptionMap` (T2). KHÔNG re-export profiler, KHÔNG VariableCodec. Api mọc dần (T7: SolverBackend; T15: registry).
2. Rewrite 47 import site conacq → `explanation.api` (profiler site → `from profiling import` đã xong T8).
3. Un-leak: 3 site conacq `_ASSUMPTION_PAIR_STRIDE` → literal `2` tạm (T5 → `slice_assumptions`).
4. `tests/test_boundary_guard.py` — AST guard 2 CHIỀU: (a) conacq→explanation chỉ qua `explanation`/`explanation.api`/`profiling`, 0 private/deep; (b) explanation KHÔNG import conacq.
5. `tests/test_transformations_characterization.py` — pin transformations.

**Green:** guard xanh 2 chiều. Docs: system-architecture (boundary + api surface).

## T5 — task_preparation dedup (safety-net TRƯỚC)

1. **safety-net trước:** `tests/test_assumption_slicer.py` pin **ID chính xác** 5 site (2 `_assign_sets` explanation + fm_oracle_model:234-240 + acqmss + quacq prep; Site 5 trên `set_c` per #4) — xanh trên code hiện tại rồi mới refactor.
2. Helper `slice_assumptions(assumptions, start, stop, stride)` (public, export api) trong `explanation/models/task_preparation.py`; migrate 5 site (4 `_assign_sets` VẪN CÒN, chỉ delegate; conacq bỏ literal `2`).
3. Trích `prepare_variable_assignments` + `_add_assignment_assumption` từ inline `fm_oracle_model` → explanation (oracle tiêu thụ ở T11.3).
4. Cleanups (ref 67bfb20): annotation, gộp ABC strategy, field chết. `_ASSUMPTION_PAIR_STRIDE` ở lại explanation (private).

**Green:** slicer test vẫn xanh (ID y hệt); đúng 1 `def slice_assumptions`.

## T6 — Model builders 2 tầng

**DELTA-CHECK (2026-07-12, brief thắng):** so với bản Bước-0:
- **+DELTA-A (item 5, sinh từ deviation T3):** dọn vestigial `DiagnosisModelBuilder.use_incremental()` + field `_use_incremental` (dead — không ai đọc; T3 rewire incremental sang `create_checker(...,is_incremental)` + `operation.with_incremental`). Xoá kèm **35** call-site chết trong `tests/test_diagnosis.py` (không phải ~12) + 3 docstring example. **GIỮ:** `PySATExplanationBuilder.with_incremental()` (operation — alive) + TOÀN BỘ conacq use_incremental (ConGen `_use_incremental`, QuAcq `use_incremental`, 2 runner, test_congen:60 — alive, đọc để dựng checker; đổi thành param operation = T11).
- **+DELTA-B (interplay):** builder chỉ dựng KB (T3); T11.4 sẽ thay body hook `_post_negation_build` bằng fold `OracleData`. T6 TẠO hook `_post_negation_build` (chứa logic post-negation hiện tại: set use_incremental + auto-prepare/prepare), T11.4 repurpose.
- **DELTA-C (filename, HOW tôi sở hữu):** đặt `OracleBiasModelBuilder` ở `conacq/oracle_bias_model_builder.py` (top-level conacq, tên khớp class; brief ghi `…/oracle_bias_builder.py`).

**Thiết kế (re-derive trên v2, KHÔNG copy tip — tip subclass body là T11-final):**
1. `explanation/models/abstract_model_builder.py` (mới) — `AbstractModelBuilder(ABC)`: **PURE template `build()` = `_validate()` + `_create_model()`** (2 hook abstract), KHÔNG state, KHÔNG `with_negation`. KHÔNG ref conacq (guard rule 4). Export qua `explanation/models/__init__.py` + `explanation/api.py`. *(Cowork review 2026-07-12: brief gốc ghi base có `with_negation`; ĐÃ SỬA — bỏ, vì 0 call-site + `_create_negation` luôn False + no-op 2/3 subclass = "setter nói dối", trùng đúng thứ item 5 vừa xoá ở use_incremental. Có caller thật thì thêm lại — YAGNI.)*
2. `DiagnosisModelBuilder(AbstractModelBuilder)` — bỏ `build()`-body (kế thừa template qua wrapper mỏng typed `-> DiagnosisModel`), `_validate`/`_create_model` sẵn có = hook impl; `super().__init__()`; `_create_model`: `needs_negation = self._for_redundancy` (≡ main). Xoá use_incremental + field + 3 docstring.
3. `OracleBiasModelBuilder(AbstractModelBuilder)` → **CONACQ** `conacq/oracle_bias_model_builder.py` — inherit qua `explanation.api`. Owns `_bias_path`/`_oracle`/`_use_incremental` + `from_bias`/`with_oracle`/`use_incremental`/`_validate`; `_create_model` = load bias → `_create_model_instance()` → set constraint_map/`_name_to_id`/`_id_to_name` → negation loop (`from explanation.api import negate_cnf_tseitin`) → `_post_negation_build(model)`. 2 hook abstract: `_create_model_instance`, `_post_negation_build`.
4. `ConGenModelBuilder(OracleBiasModelBuilder)` — giữ examples methods; hook `_create_model_instance→ConGenModel()`, `_post_negation_build`: `model._use_incremental=...` + auto-prepare-if-examples. `QuAcqModelBuilder(OracleBiasModelBuilder)` — hook: `_create_model_instance→QuAcqModel()`, `_post_negation_build`: `model.use_incremental=...` + pos/neg assignment maps + `model.prepare(oracle)`.
5. **KHÔNG tạo `last_task`** (artifact tip; main không có).

**Green:** additive; `test_congen`/`test_quacq`/`test_diagnosis` xanh; guard 5-rule (đặc biệt rule 4 explanation⊥conacq + rule 1 conacq→explanation qua api). Suite ≥384.

## T7 — Consistency-checker port + backend adapters (formalize seam T3)

**Cowork review 2026-07-12 (đã sửa trọn):** phiên đầu ĐẢO NGƯỢC tên port/adapter. Bằng chứng: `checker.py` import `pysat.solvers.Solver`+`subprocess`+`jar_path` = ADAPTER nói-với-solver; còn `ConsistencyChecker` 73 lần/24 file chỉ 3 chỗ subclass → ~70 chỗ dùng như PORT. Sửa: **PORT giữ tên `ConsistencyChecker`** (chỉ đổi *là gì* ABC→Protocol, *ở đâu* = ở checker.py sạch pysat/subprocess), **ADAPTER = `*Backend`** ở solver_backend.py. Bán kính rẻ: ~70 site annotation KHÔNG đổi chữ.

**Thiết kế (đã impl + xanh):**
- `explanation/operations/algorithms/checker.py` = **PORT** (0 import pysat/subprocess): `ConsistencyChecker` (Protocol @runtime_checkable: is_consistent/get_model/cleanup) + `TestCaseChecker(ConsistencyChecker)` (+is_consistent_test_cases). *~70 consumer giữ `ConsistencyChecker`.*
- `explanation/operations/algorithms/solver_backend.py` = **ADAPTER + dựng**: `AbstractSolverBackend(ABC)` (profiler/_compute_delta/is_consistent_test_cases loop/copy/pickling/ctx-mgr) + `IncrementalPySATBackend`/`NonIncrementalPySATBackend`/`SAT4JBackend` + `BackendConfig` (public enum) + `BackendConfig.from_flags(use_incremental,use_sat4j)` + **`build_checker(task, config, solver_name, profiler)` = CỬA CÔNG KHAI DUY NHẤT (task-based)** + `_build_backend(config, set_kb, assumptions, …)` PRIVATE = **điểm chọn-class DUY NHẤT** (token→class). Import port TOP-LEVEL → **acyclic, KHÔNG lazy-import** (cycle phiên đầu là do đảo tên/vị trí — đã tan).
- `CheckerFactory` **HOÀ TAN** (class 2 @staticmethod = Java-ism). 4 conacq + ~7 test call-site `create_from_task`/`create_sat4jchecker` → `build_checker(task, BackendConfig.from_flags(...))`. Ma trận test_diagnosis (use_sat4j×is_incremental) giữ độ phủ (1 helper `build_checker(task, from_flags(...))`).
- **Điểm quyết định thứ 2 (phiên đầu SAI claim=1):** `generate_ne.py:115` hardcode `NonIncrementalPySATChecker(set_kb,assumptions)` (không if → grep miss). SỬA: dựng `DiagnosisTask(set_c=set_tv, set_b=set_bg, set_kb, assumptions)` → `build_checker(task, BackendConfig.PYSAT_NON_INCREMENTAL)` → `find_conflict(task.set_c, task.set_b)`. Bất biến T3 "checker luôn từ Task" giữ → cửa public chỉ cần task-based.
- Retype: diagnosis path (pysat_abstract_explanation/conflict/diagnosis) → `ConsistencyChecker`; 2 algo standalone (quickxplain_with_testcases/kbdiag) → `TestCaseChecker`.
- `api.py`: BỎ mọi tên class adapter + CheckerFactory; chỉ export `ConsistencyChecker`, `TestCaseChecker`, `BackendConfig`, `build_checker`. Test import sâu solver_backend (được phép).

**Nghiệm thu (verified):** `*Backend(` chỉ solver_backend.py (_build_backend=1 + 3 copy self-clone); checker.py 0 pysat/subprocess; 0 lazy-import; suite 395 passed 0 failed; guard 5-rule; byte-identical.
**Green:** additive. *(A3 sat4j đã xử ở T3.)*

### Cụm commit T7 (Cowork chốt 2026-07-12 — mỗi commit xanh+guard+DỪNG-duyệt)

- **commit 0 — docs: ADR-0001..0006** ✅ (dc217c6). ADR do Cowork sở hữu; CC không sửa, thấy sai thì báo.
- **commit 1 — T7** (rename port/adapter + **A2** `CopyableChecker(ConsistencyChecker)` cho `copy()` [fastdiagp gõ theo, export api→5 symbol] + **m1** SAT4J except thu hẹp+`from e` + **m2** `CheckerBase.__init__` khai `assumptions`). GREEN 396. `implements ADR-0004`.
- **commit 2 — T7b (code-review remediation):** **A1/A3 [Cowork đảo T2, ADR-0007]** — GỠ HẲN read-only MappingProxyType view (tồn tại chỉ để test chính nó xanh; grep: caller mutate catalog duy nhất = `test_encoding:71`; 0 production). `KBModel` = 5 field dict phẳng (bỏ property/view/memo/`_name_to_id`); 3 model con + builder gán thẳng `name_to_id`/`id_to_name`. `DiagnosisModel` GIỮ 2 property (lớp phiên dịch flamapy `variables`/`features`→tên KBProtocol) nhưng bỏ proxy (`return self.features`). `KBProtocol` giữ `Mapping` (dict là Mapping → structural OK, read-only ở tầng type, runtime 0đ). A3 tự biến (feature_ids đã là dict). GIỮ hoist `fm_oracle:83`. Xoá read-only assertion test. **Benchmark (1 máy):** v2-proxy 342.7µs → v2-plain 275.0µs = **−20%** (khớp reviewer −25%); main không đo được trên máy này (worktree main khoá + hook chặn .git) nhưng main tiền-T2 = plain-dict = đúng đường v2-after. · **A5** frozen-contract THẬT (docstring shallow-frozen + test rebind→FrozenInstanceError, in-place cho phép; **T11b** deep-freeze) · **m3** docstring "variables" · **m4** 2 runner `build_checker(task,…)` · **m5** generate_ne `with … as checker:` · **m6** `PreparedTask` frozen · **m8** `id_assumption = prepare_configuration(...)`. **Commit kèm:** `docs/adr/0007-no-runtime-read-only-views.md` + adr README (quyết định đi liền việc hiện thực).
- **commit 3 — refactor: chuyển port+adapter RA KHỎI operations/algorithms/** (chèn Cowork 2026-07-12; checker/solver_backend là *thứ thuật toán tiêu thụ*, không phải thuật toán → ngăn kéo tạp). NEW package `explanation/checker/`: `protocols.py` (PORT 3 protocol, 0 pysat/subprocess) + `backend.py` (ADAPTER: **`CheckerBase`** [đổi từ SolverCheckerBase, bỏ "Solver" thừa] + 3 `*Checker` + `SolverBackend` enum + `build_checker`) + `__init__.py` (facade NỘI BỘ, KHÔNG phải cửa thứ 2; api.py vẫn cửa DUY NHẤT). **GỘP `_build_checker`→`build_checker`** (1 hàm chứa if/else; helper 1-caller = indirection thừa vì deviation-1 đã bị bác); annotate `task: Task`; test đi qua cửa công khai (dựng DiagnosisTask). Rewrite ~24 import site. **Xoá xác** `explanation/operations/algorithms/profiler/` (rỗng, 0 git-track, xác T8). Docs cây+inventory. Nghiệm thu: `ls operations/algorithms/` hết checker.py/solver_backend.py/profiler/; `grep _build_checker`=0; điểm chọn class=1 (thân build_checker); api 5 symbol; guard 5-rule; byte-identical.
- **commit 4 — fix: SAT4J timeout** → `raise SolverTimeoutError` (thay `output="TIMEOUT"`→UNSAT-im-lặng). **ĐỔI HÀNH VI** (phạm "y hệt main") → commit riêng; message cảnh báo: nếu timeout từng xảy ra trong lần chạy paper thì kết quả có thể sai (rủi ro thấp — PySAT chính, SAT4J chỉ cross-validate).

**Nợ ghi (KHÔNG làm trong cụm):** A6 (`get_c()` nhiễm query cuối — có trên main) → **T11.2** + nghiệm thu tường minh · m7 (`solver_name` tham số chết trong ma trận test) → **T13** · **BỎ #9** (động cơ an toàn đã do read-only view T2 mua; động cơ perf là ảo — chi phí thật ở A1).

## T9 — Runners + metrics (export ĐÔNG CỨNG)  — SPEC: `Cowork/explanation/t9-design.md` (đã DELTA-CHECK 260712)

Main/v2: `performance_metrics.py` 652 LOC (`PerformanceMetrics` ~29 field + `AggregatedPerformanceMetrics` ~100 field + `aggregate_metrics` ~195 dòng + `_stat4`); container tiêu thụ CHỈ bởi `cross_validation.py:213` (`get_performance_metrics`) + `:274` (`aggregate_metrics`); runner ① hand-extract `congen_runner:196-209` / `quacq_runner:282-311`; deferred import `base_runner:60`; `quacq_runner:23` `from ..eval import` (relative); `congen_runner:20` absolute. Read-path KHÔNG chạm perf groups mở rộng: `extract_results.load_cv_result` đọc CHỈ 4 group (runtime/consistency_checks/memory/kb_size), `result_loader.from_json` KHÔNG đọc `performance`. ⇒ disjoint an toàn với byte-identical.

**BƯỚC 1 — LƯỚI TRƯỚC (green trên code CŨ, chưa refactor 1 dòng):**
1. Snapshot: `python -m apps.extract_results` trên `data/results/**` (code CŨ) → `paper/tables/*` (chuẩn byte-diff).
2. `tests/test_t9_metrics_safety_net.py`: **test 1** extraction-diff (nghiệm thu thật, byte-identical), **test 2** schema-pin bằng LITERAL (ConGen: 13 group prefix từ file thật; QuAcq: group zeroed nhúng trong file congen), **test 3** from_json sweep mọi JSON `data/results/**`. XANH TRÊN CODE CŨ trước.

**BƯỚC 2 — REFACTOR:**
3. **`conacq/runners/metrics.py` (MỚI)** — `Kind` enum (COUNTER/TIMER_SEC/GAUGE) + `MetricSpec(key/source/kind/group/unit/stats)` frozen + **hai bảng disjoint module-level** `CONGEN_METRICS`, `QUACQ_METRICS` (ba không-gian-tên khai báo tường minh: abbrev on-disk sống ở `group`) + `RunMetrics(spec,values)` dict-backed (`to_dict` DẪN XUẤT từ spec) + `collect(profiler,spec)` (thay ①) + `aggregate(runs)` generic ~40 LOC (thay ③④), áp quy tắc §3.2 (1 metric→`{stat}{unit}`; >1→`{key}_{stat}{unit}`).
4. **Dời container** khỏi `eval/`: xoá `performance_metrics.py`; `base_runner`/`congen_runner`/`quacq_runner` import `.metrics` (bỏ 3 kiểu import eval); `cross_validation.py` import `aggregate` từ `conacq.runners.metrics` (eval→runners = chiều ĐÚNG); xoá deferred import `base_runner:60`; `eval/__init__` bỏ export container.
5. **Guard rule 6** (`tests/test_boundary_guard.py`): `conacq.{runners,algorithms,models,oracle,bias,examples}` KHÔNG import `conacq.eval` — bắt CẢ absolute (`conacq.eval[.x]`) LẪN relative (`from ..eval import`). ADR-0006.
6. **Dời `conacq/eval/config.py` → `conacq/config.py`** (app config, không phải eval); cập nhật 5 app (`run_evaluation/run_cv/run_congen/run_compare/run_quacq`) + `eval/__init__` bỏ export config.  *(D7: brief ghi "six apps" — thực 5, lệch cơ học → Cowork sync brief.)*
7. [71c1511] `ConGenRunResult` + `result_loader.ConGenResultData` → `UnifiedConGenResult` (`conacq/runners/unified_result.py` mới); `from_json` vẫn đọc JSON cũ `data/results/**`; cập nhật `runners/__init__` + `kb_comparator`/`cross_validation` consumers.

**BƯỚC 3 — LƯỚI SAU:** **test 4** metric-map completeness (mọi profiler-key runner emit ∈ table HOẶC IGNORED list); **test 5** disjointness (CONGEN_METRICS ∩ QUACQ_METRICS = ∅ ngoài core khai báo). Cập nhật `test_evaluation.py::TestPerformanceMetrics` sang API mới (giữ coverage, KHÔNG làm yếu).

**Green:** suite ≥ 400 + test mới; diff `paper/tables/*` RỖNG; `data/results/**` from_json-readable; điểm khai báo metric = 1; guard 6-rule; `grep "from conacq.eval" conacq/runners/` = 0; `performance_metrics.py` 652→~190. Docs in-stage: eval-pipeline.md + codebase-summary.md + system-architecture.md.

**DELTA-CHECK 260712 (design thắng):** D1 thêm `metrics.py` (impl-plan cũ chỉ có unified_result). D2 bảng disjoint module-level (không "trên BaseRunner"). D3 thêm guard rule 6. D4 thêm config move. D5 dùng 5 test §4 (extraction-diff = nghiệm thu thật). **D6 BỎ [A4] dedup shuffle+profiling boilerplate** → nợ T17. D7 6 core subpackage thực = algorithms/bias/example_generators/examples/oracle/runners (design ghi 'models' — không có trong conacq); 5 app import config (không 6).

**TRẠNG THÁI 260712:** BƯỚC 1–3 xong + XANH (suite 407, net 7 test, guard 6-rule), **committed `20cfae8`**.

**Item 7 (UnifiedConGenResult, `71c1511`) — ❌ BÁC BỎ (không hoãn).** Phân tích 260712 (đã verify trên code): `ConGenRunResult` = sản-phẩm-GHI (mang `metrics: RunMetrics` sống + `kb_clauses` CNF + `profiler_data`); `ConGenResultData` = phép-chiếu-ĐỌC (7 field JSON thuần) — không consumer nào (kb_comparator/progressive_evaluation/run_compare) cần phần ghi. 6-field-overlap = từ vựng domain, KHÔNG phải cùng-schema. Gộp = ghép read với write, phá đúng vách khiến T9 byte-identical miễn phí. Phương án mixin cũng loại (0 hành vi, chỉ thêm gián tiếp + ép đồng bộ hai bên đáng lẽ tự do lệch). **Chốt ở `docs/adr/0008-run-result-and-result-data-stay-separate.md`.** T9b XOÁ khỏi lộ trình.

## T10 — apps CLI harness + logging + atomic writes  (DELTA-CHECK 260712)

Neo (Cowork đo): print apps=254 · conacq=20 · explanation=9 · profiling=22. 5 app run_* ≈ 1180 LOC lặp argparse+config+error. **3 COMMIT tách bạch; A trước (an toàn dữ liệu).**

**Commit A — fix: atomic writes (LÀM TRƯỚC).** Mọi writer là `open(path,'w')` → cắt cụt tức thì; crash giữa chừng (SAT4J timeout giờ RAISE ở chỗ trước im lặng — commit d72cc86) ⇒ file kết quả cũ mất sạch.
- `conacq/atomic_io.py` (mới): `write_text_atomic(path, text)` + `write_json_atomic(path, data, indent=2)` — temp CÙNG thư mục (os.replace chỉ atomic trong 1 filesystem) → `flush()`+`os.fsync()` → `os.replace()`. **Chọn `conacq/` root** (KHÔNG `apps/_io.py`): writer sống ở CẢ `conacq/eval` LẪN `apps`; đặt ở apps → eval phải import apps = ngược tầng. Tên `atomic_io` (né shadow stdlib `io`). Chỉ import stdlib → 0 cycle, ngoài guard rule 6.
- **10 writer / 6 file** (đã grep — 2 ngoài list Cowork: `run_compare:211` eval_file, `folds.py:94` fold data): json ×7 (`eval/report:279`, `eval/folds:94`, `run_cv:192`, `run_evaluation:152`, `run_compare:151,211`) + text ×3 (`extract_results:754` md, `:759` tex, `generate_bias_config:449` yaml).
- Format KHÔNG đổi: `json.dumps(indent=2)` ≡ `json.dump(indent=2)` byte-identical; text ghi nguyên chuỗi. ⇒ lưới T9 (extraction diff) vẫn xanh.
- **Test bắt buộc** `tests/test_atomic_io.py`: ghi đè file có sẵn, raise giữa chừng (monkeypatch `os.replace`) → file cũ NGUYÊN VẸN + 0 temp rác; serialize lỗi → cũ nguyên; byte-identical vs `json.dump`.

**Commit B — refactor(apps): `apps/_harness.py`** — argparse skeleton (config path, -v/--verbose) + setup logging + load TOML + bọc lỗi; 10 app dùng chung. Nghiệm thu: `python -m apps.<app> --help` chạy; flag KHÔNG đổi tên/nghĩa.

**Commit C — refactor: print() → logging.** 254+20+9 print → `logging.getLogger(__name__)`; chain `raise ... from e`. **Allowlist GIỮ:** `user_prompt` (I/O tương tác oracle-người) + `profiling` `print_summary()` (output-method có chủ đích — kiểm từng cái; leaf KHÔNG import logging-config app). **⚠️ PRE-CHECK:** có script/Makefile/notebook parse stdout app (`| grep`, `> file`) không → nếu có DỪNG hỏi Cowork (print→log đẩy sang stderr, vỡ im lặng).

**Green mỗi commit:** suite ≥ 407; guard 6-rule; lưới T9 xanh; A: crash-test; B: `--help` ×10; C: `print(` sống = 0 ngoài allowlist. Docs in-stage (eval-pipeline/README nếu đổi).

## T11 ⚠️ — Oracle arc (rủi ro cao nhất, green-gate từng sub-step)

Main anchors: `base.py` Oracle ABC stub (get_variables:38, complete_configuration:41); `fm_oracle_model` `_base_set_c:47` / `with_configuration:121-130` / `prepare:133,189` / `_bg_data` lazy+RuntimeError:51-74 / fold:234-247; `fm_oracle.complete_configuration:116` dựng `Solver()` mỗi call:134.

- **11.0 safety-net TRƯỚC:** `tests/test_oracle_hotpath_safety_net.py` + `tests/test_prepare_task_content_safety_net.py` — pin hot-path oracle + nội dung task ConGen/QuAcq **gồm negatives** (`set_neg_tv`/`negation_map`) + fixture ConGen negative; pin thêm [#1] giá trị/thời điểm `bg_data`, [#10] kết quả `complete_configuration`, [#4] `get_c()`/Site 5.
- **11.1 [#2]:** Oracle → protocol hẹp `Membership/Catalog/Completable/BGProvider` (`conacq/oracle/base.py`); dời catalog (get_variables/feature_ids/constraint_count/next_id/fm_clauses…) xuống `FMOracleModel`; `FeatureModelOracle` mỏng = membership + facade. KHÔNG micro-class.
- **11.2 [#4]:** FMOracle purity — KHÔNG khai `base_set_c`; `prepare` set `result.set_c` (FM-only); `is_valid`/`get_c` đọc `task.set_c` cục bộ (`task.set_c + config_to_assignment_assumptions(...)` — không mutate); **xoá `with_configuration`+`dataclasses.replace` tạm của T1**; bỏ plumbing `_FMPrepResult`/`PreparationOutput`; sửa `test_oracle_model.py` (4 chỗ) + Site 5. `GenerateNE` KHÔNG sửa.
- **11.3:** oracle dùng `prepare_variable_assignments` chung (từ T5).
- **11.4 ⬆️ NÂNG CẤP (ADR-0009 — tách vai):** `conacq/oracle/oracle_data.py` (mới) — **`OracleData`** frozen snapshot fold lên model lúc `build()`, implement **`BGProvider` + `KBProvider`** (= composite `PreparationOracle` của T11.1 — ĐÓ chính là hình dạng OracleData; đừng xoá). Job ② (`get_bg_data`/`get_root_clauses`/`get_kb`/`get_assumptions`/`get_c`) rời KHỎI oracle sang OracleData; `GenerateNE` + 2 task_prep + builders nhận OracleData, KHÔNG nhận oracle sống. A6 tan **theo cấu trúc** (oracle không sở hữu thứ nó từng làm nhiễm). `ConGenModel.prepare_task` bỏ tham số oracle; `QuAcqModel.prepare_task(task_input=None)` từ chối non-empty; [#3] `FMOracleModel.prepare_task` fail-fast `assert task_input is None`; [#1] `bg_data` **eager trong `build()`**, prepare_task pure (bỏ cache + RuntimeError thứ-tự-gọi).
  - **Nghiệm thu MỚI (ADR-0009):** `assert not isinstance(FMOracle(...), KBProvider)` + `assert not isinstance(FMOracle(...), BGProvider)` — job ② đã rời oracle. (T11.2 sửa `get_c()` chỉ chữa triệu chứng; T11.4 chữa cả LỚP bug.)
- **[nợ T7] Dời `GenerateNE`** — hiện xếp nhầm ở `conacq/algorithms/` (export trong `algorithms/__init__.__all__`, đọc oracle SỐNG, caller duy nhất = `ConGenTaskPreparation` task_preparation.py:162, KHÔNG trong vòng lặp giải). Dời vào `task_preparation` + BỎ export `__all__`. Làm CÙNG fold OracleData (11.4) vì cùng vùng prepare/oracle.
- **11.5 [#10]:** `complete_configuration` giữ MỘT solver bền; per-call chỉ solve dưới assumptions. Safety-net 11.0 canh kết quả.

**Green cuối:** 4 model cùng chữ ký `prepare_task(task_input) -> PreparedTask`; model pure; `base_set_c` = 0 hit; hành vi diagnoses/membership/completion Y HỆT baseline; guard 2 chiều xanh. Docs: system-architecture oracle section + congen.md/quacq.md nếu đụng.

**✅ 11.0 thực thi (NET-ONLY, staged — theo `t11-safety-net.md` 4 lớp, thay thiết kế 2-file ở dòng 190):**
- **Rule #1:** `git diff --stat` trên `conacq/oracle` · `conacq/algorithms` · `explanation/models` = RỖNG. Chỉ file test/fixture/script MỚI.
- **L1 trace** (`test_t11_oracle_trace_net.py`): record&replay 14 getter + is_valid×220 + completion trên REAL-FM-7·arcade·busybox(slow). Golden JSON đóng băng (recorder `scripts/build_t11_oracle_net_fixtures.py`), snapshot get_c TRƯỚC query ⇒ không mã hoá A6. Fixture thiếu ⇒ **FAIL**, không skip.
- **L2 ID golden** (`test_t11_prepared_task_ids.py`): 7 factory DiagnosisModel + ConGen/QuAcq prep + **GenerateNE per-testcase** (ne_id/ne_clause/set_kb growth — seam A6-nhiễm + T11.4 relocate).
- **L3 E2E** (`test_t11_e2e_learned_kb.py`): ConGen RS(kb=17,n_mss=78)·FF(kb=18,n_mss=102); QuAcq học KB RỖNG tới 500 query ⇒ pin **query_history** (15-query trajectory) + convergence. *(diagnoses không phải attr; pin kb_assumption_ids/n_mss/n_kb.)*
- **L4+A6 guard** (`test_t11_purity_guards.py`): **8 `xfail(strict)`** (A6 get_c-invariant · with_configuration · prepare_task-unified · OracleData-frozen[import `conacq.oracle`] · base_set_c=0 · no RuntimeError · GenerateNE off `__all__` · complete_config-1-solver). Tất cả ĐỎ đúng lý do, 0 XPASS. Cờ cứng: 8 guard đỏ hôm nay (spec ghi 4).
- **Gate:** suite **445 + 8 xfailed** · guard 6-rule xanh · lưới T9 xanh. **Bug thấy-KHÔNG-sửa:** A6 pollution (đã pin A6 xfail). *(QuAcq KB rỗng trong test-setup này = artifact bias/example, KHÔNG phải lỗi — recall thật ghi trên REAL-FM-7 ~1–3%, n_kb 1–6/~100: yếu nhưng khác 0, đúng hành vi. Trajectory-pin vẫn đủ: T11 chỉ đụng oracle, L1 pin mọi câu-trả-lời + trajectory pin mọi câu-hỏi ⇒ cùng thứ học được theo cấu trúc.)*

**✅ 11.1 thực thi (type-only, additive-green — gộp rename ADR-0009 trong 1 commit):**
- `conacq/oracle/protocols.py` (mới): 5 vai atomic (`MembershipOracle`/`CompletableOracle`/`CatalogProvider`/`BGProvider`/`KBProvider`) + 2 composite (`GeneratorOracle`, `PreparationOracle`) `@runtime_checkable`. **KBProvider** = bề mặt A6-nhiễm, consumer duy nhất GenerateNE.
- **Đo consumer thật** (không theo trực giác): thêm 2 method vào protocol theo usage đo được — `ask` KHÔNG vào Membership (test phân biệt cần stub chỉ-`is_valid`; verify 0 runtime `oracle.ask()`), `get_root_clauses` vào BGProvider (congen_model dùng). ~14 consumer site retype về protocol hẹp; 0 consumer gõ `FMOracle`.
- **Catalog xuống `FMOracleModel`** (`get_variables`/`get_variable_ids`), oracle facade delegate — hành vi y hệt.
- **Rename ADR-0009 (gộp, không commit trung gian):** `FeatureModelOracle`→`FMOracle` (0 residual); `get_feature_ids`→`get_variable_ids` (chỉ oracle protocol/impl; BiasConfig.get_feature_ids + FMData.feature_ids GIỮ — concrete FM-specific). Golden key `"get_feature_ids"` GIỮ nguyên (nhãn recording) ⇒ `git diff tests/fixtures/` RỖNG.
- **Gate:** suite **456 + 8 xfailed** (0 XPASS) · 13 characterization + 11 protocol xanh · guard 6-rule xanh · fixtures RỖNG. `not isinstance(FMOracle, KB/BGProvider)` CHƯA đúng (đó là T11.4).

## T11b — Post-oracle cleanup block (làm SAU T11, một lượt sửa api/guard/docs)

Gom các nợ đụng builder/prep-hierarchy + api T12 (đã đóng băng) → làm chung sau khi T11 tái cấu trúc prep arc:
1. **Generic[TModel] cho builders** — `AbstractModelBuilder.build()`/`_create_model()` + `OracleBiasModelBuilder._create_model_instance()` đang gõ `Any` → mất type safety (T6 chấp nhận tạm). Dùng `Generic[TModel]` để `build()` trả đúng kiểu model. *(nợ sinh ở T6)*
2. **Gộp twin ABC prep-strategy** — `DiagnosisTaskPreparationStrategy` + `TestCaseTaskPreparationStrategy` là bản sao thuần; gộp (cân nhắc `Generic[T]`), cập nhật export api `TestCaseTaskPreparationStrategy` + base conacq `ConGenTaskPreparation`. *(nợ hoãn từ T5)*
3. **#8 AssumptionIdAllocator** — thay cấp-phát ID assumption thủ công. *(cùng vùng prep hierarchy)*
4. **[nợ T7b, NGHIỆM THU CỨNG] Task bất biến SÂU** — hiện chỉ shallow-frozen (rebind chặn, in-place không). Cơ chế: `__post_init__` + `object.__setattr__` → `set_c/set_b/assumptions: Tuple[int,...]`, `set_kb: Tuple[Tuple[int,...],...]`. **⚠️ `negation_map` PHẢI ở lại dict** — MappingProxyType không pickle được → vỡ FastDiagP multiprocessing. **Bán kính đã đo:** `set_kb.append` toàn ở local trước khi dựng Task (build-then-freeze) → 0 ảnh hưởng; `task.set_kb`→PySAT `bootstrap_with`+DIMACS writer nhận tuple-of-tuple OK; vỡ ~8–12 `.copy()`→`list(...)` (wipeoutr_fm:64, wipeoutr_t:71/74, kbdiag:109, acqmss:71, cây labeler). **Nghiệm thu CỨNG (user):** XOÁ docstring shallow-frozen + XOÁ test `test_task_is_only_shallow_frozen`, THAY bằng test pin `raises` khi mutate in-place. *(docstring shallow-frozen hiện tại = giấy nợ có ngày đáo hạn, không phải lời bào chữa)*

**Green:** additive/refactor; suite ≥ hiện tại; guard 5-rule; api/docs sửa một lần.

## T13 — Labelers + split test_diagnosis

Main: 5 file labeler (`hsdag/labeler/`); `test_diagnosis.py` 1328 LOC unittest+parameterized.

1. Template base cho labeler (gom khung lặp 4 concrete).
2. Migrate `test_diagnosis` → pytest; **tách 5 file theo thuật toán** + `tests/diagnosis_support.py`; doc twin-algorithms (cố ý tách rời).
3. **[nợ T7] Retype cây labeler theo role** — `IHSLabelable.get_instance(checker: …)` đang gõ `ConsistencyChecker` (port hẹp) nhưng `kbdiag_labeler` gọi `is_consistent_test_cases` → static-variance. Sửa: kbdiag_labeler → `TestCaseChecker`; cân nhắc `Generic[TChecker]` cho cây (T13 sở hữu cây labeler). Runtime hiện an toàn (no mypy-gate).

**Green:** tổng số test không đổi (đếm trước/sau).

## T14 — IO base

1. `conacq/_io_base.py` (mới) — mixin JSON IO; `BiasIO` (bias_io.py:14) + `ExampleIO` (io_utils.py:14) kế thừa.
2. Format on-disk GIỮ (indent=2). `tests/test_io_base_roundtrip.py`.

## T15 — Op registry + redundancy first-class

Main: `PySATRedundancyConstraints(PySATDiagnosis)` (:17), `PySATRedundancyTestCases(PySATTestCase)` (:16) = inherit-then-stub; builders ở `pysat_explanation_builder.py:293,356`.

1. Redundancy ops → first-class (bỏ inherit-then-stub), builders cập nhật.
2. `explanation/operations/registry.py` (mới) — registry op, seam plugin; export qua api.

**Green:** `test_diagnosis_redundancy.py` xanh.

## T16 — Generators seeded-RNG

Main (đã verify — brief lệch cơ học): RNG global ở `base.py:71-74`, `feature_frequency.py:49,186-222`, `random_sampling.py:45,57`, **`query_provider.py:56`** (nwise_coverage KHÔNG dùng random).

1. **safety-net:** `tests/test_generator_characterization.py` pin sequence seeded hiện tại (`random.seed(s)` global ≡ `random.Random(s)` cùng MT sequence → hành vi giữ).
2. `random.Random(seed)` instance per-generator, không đụng global, ở 4 file trên.

**✅ Thực thi (staged, chưa commit):**
- 4 file refactor: `base.py` (`self._rng` default `__init__` + `_generate_valid_config`), `random_sampling.py` (3× `generate`), `feature_frequency.py` (`generate` + 2 helper), `query_provider.py` (gộp nhánh `seed=None` → `random.Random(seed).shuffle`).
- safety-net `tests/test_generator_characterization.py` (14 test): 4 test isolation ĐỎ trên code cũ (chứng minh refutable) → XANH sau refactor; 10 test reproducibility XANH cả hai chiều.
- **Đã verify oracle/SAT path KHÔNG dùng `random.*` toàn cục** ⇒ sequence seeded GIỮ NGUYÊN vs main; **0 golden đỏ** (suite 431 pass).
- **Delta resolved:** `query_provider.py:56` XÁC NHẬN là file thứ 4 (handoff cũ ghi "không dùng random" là drift — code thực có `random.shuffle(self._pool)` ở nhánh `seed=None`). `nwise_coverage.py` không dùng random.
- Gate: suite **431** (≥417) · guard 6-rule xanh · T9 extraction-diff xanh · grep 0 `random.*` toàn cục trong `example_generators/`.

## T17 — Dead-code cleanup

1. Chuyển `tests/test_bias_module.py` + `test_bias_module_1.py` → `scripts/` (demo, đổi tên `*demo*`).
2. Xoá comment cũ/field chết còn sót (ref fda29d7 + 67bfb20, **TRỪ** phần xoá dimacs).
3. ⚠️ **GIỮ `explanation/transformations/dimacs_to_configuration.py`**.
4. **[nợ T9, A4] Dedup runner-lifecycle boilerplate** — `collect(profiler, spec)` đã nuốt phần trùng nặng nhất (30 dòng get_metric ×2). Phần còn lại (profiler_session start/stop + tracemalloc + shuffle) vẫn lặp ở `congen_runner`/`quacq_runner`. Hoist lên `BaseRunner` nếu đáng. *(Cowork duyệt hoãn khỏi T9 — ngoài scope design metric-only.)*

**Verify:** grep symbol đã xoá = 0; dimacs file còn.

## T4 — ConsistencyExecutor + viết lại FastDiagP (TASK CUỐI)

Main: `fastdiagp.py` `lookup_table:42` + `mp.Pool:76`; profiling còn `ProfilerMode`/multiprocess (giữ từ T8).

1. **4.1** `explanation/operations/algorithms/executor.py` (mới): `ConsistencyExecutor` Protocol (`is_consistent/solve/submit→Future`) hợp nhất serial (`ConsistencyChecker`) + parallel.
2. **4.2** `ProcessExecutor`: `mp.Pool` chung; `_pool_init` dựng checker worker 1 lần từ KB (không pickle solver sống); đếm CC ở MAIN; worker `NullProfiler`; worker trả `(bool, elapsed)` → main ghi `solver_time`.
3. **4.3** `MemoizingExecutor`: `ConsistencyCache` (hash-assumptions→bool) + `_pending` Future + lock (dedup in-flight, fix bug đếm trùng). HIT ≠ CC.
4. **4.4** FastDiagP rewrite: bỏ `self.pool`/`self.lookup_table`; `__init__(executor)`; lookahead → `executor.submit`; gauge → `len(executor.cache)`.
5. **4.5** Xoá `ProfilerMode`/multiprocess chết trong `profiling/`; `tests/test_executor.py` (parity serial≡parallel CC-count, memo-hit, lookahead canary) + fixture `tests/resources/prod_4_1.cnf` (tham khảo tip).

**Green:** 2 task từ 1 KB song song; CC serial≡parallel; diagnoses y hệt baseline. Docs: system-architecture (executor).

## T18 — Docs coherence pass (chỉ đọc-soát)

Đọc-soát nhất quán toàn cục: README (install + Quick-Start — lưu ý drift ghi ở Bước-0 §3.7 sẽ tự khớp), `project-roadmap` (trạng thái), `system-architecture` overview, `codebase-summary` inventory. KHÔNG đổi hành vi.

---

## Nghiệm thu cuối (từ brief "Nghiệm thu cuối")

1. `PYTHONPATH=. pytest tests/ -v` xanh, **≥ 593 test**.
2. Guard 2 chiều xanh · `print()`=0 (trừ user_prompt) · CV-JSON atomic · CSV/LaTeX byte-identical (vs snapshot T9) · `base_set_c`=0 hit · explanation KHÔNG import conacq.
3. Hành vi diagnoses/membership/completion y hệt main. Docs in-stage đủ.
4. Báo cáo cuối trong thư mục này: câu-hỏi-design (nếu có) + vùng phân kỳ có-chủ-đích.

## Vùng phân kỳ CÓ CHỦ ĐÍCH vs tip (review từng vùng, không phải lỗi)

`profiling/` top-level (tip: trong explanation) · `OracleBiasModelBuilder` ở conacq (tip: explanation) · `dimacs_to_configuration.py` GIỮ (tip xoá) · KHÔNG `VariableCodec` (tip có) · KHÔNG `base_set_c`/`last_task` (tip có) · `OracleData` (tip: `OracleTaskData`) · #1/#2/#3/#6/#8/#9/#10 per brief · guard 2 chiều (tip: 1 chiều).

## Unresolved questions

- Không có câu hỏi design chặn. 7 lỗi cơ học brief↔main → Bước-0 report (Cowork đồng bộ brief; không đổi quyết định).
- Vị trí file mới chưa chốt trong brief (tôi đề xuất, user chỉnh được khi review task): `explanation/models/kb_protocol.py`, `conacq/kb_model.py`, `conacq/oracle_bias_model_builder.py`, `conacq/oracle/oracle_data.py`.
