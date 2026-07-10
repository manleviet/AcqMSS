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

1. `explanation/models/abstract_model_builder.py` (mới) — universal ABC (with_negation/build template, KHÔNG ref conacq); `DiagnosisModelBuilder` kế thừa.
2. **`OracleBiasModelBuilder` → CONACQ** (file mới, đề xuất `conacq/oracle_bias_model_builder.py`) — *cố ý khác tip* (tip để ở explanation = leak framework→app). Inherit AbstractModelBuilder qua api.
3. `ConGenModelBuilder/QuAcqModelBuilder(OracleBiasModelBuilder)`. **KHÔNG tạo `last_task`**.

**Green:** additive; `test_congen`/`test_quacq` + guard 2 chiều xanh.

## T7 — SolverBackend port (formalize seam T3)

1. `explanation/operations/algorithms/solver_backend.py`: `SolverBackend` Protocol @runtime_checkable (`is_consistent/get_model/cleanup` — 3 checker thoả) + `_BackendConfig` enum + `build_solver_backend(config,…)` (1 nơi map token→checker).
2. Ops gõ theo Protocol; export `SolverBackend` qua api.
3. `tests/test_solver_backend_port.py`.

**Green:** additive. *(A3 sat4j đã xử ở T3.)*

## T9 — Runners + metrics (export ĐÔNG CỨNG)

Main: `base_runner.py` **đã tồn tại** (modify); `performance_metrics.py` 652 LOC / `_stat4` ×25; `result_loader` ở `conacq/eval/`.

1. **Snapshot export TRƯỚC:** chạy `apps/extract_results` trên `data/results/**` hiện có → lưu CSV/LaTeX vào scratchpad làm chuẩn byte-diff.
2. **safety-net:** `tests/test_runmetrics_aggregation.py` pin số liệu aggregation hiện tại.
3. [A4] `BaseRunner` sở hữu profiling + metric map khai báo; 2 runner bỏ lặp shuffle+profiling.
4. [C2] Reducer metric tổng quát thay 25 khối `_stat4`.
5. [71c1511] `conacq/runners/unified_result.py` (mới) `UnifiedConGenResult` + cập nhật `result_loader` (`from_json` đọc được JSON cũ trong `data/results/**`).

**Green:** suite + diff CSV/LaTeX **rỗng** vs snapshot. KHÔNG regenerate `data/results/`. Docs: eval-pipeline.md.

## T10 — apps CLI harness + logging

Main: print apps=254, conacq=20, explanation=31 (thô, gồm docstring).

1. `apps/_harness.py` (mới): parse config TOML + verbose + logging setup dùng chung; migrate `apps/*.py`.
2. **CV-JSON atomic:** tìm site ghi (`grep -rn "json.dump" conacq/eval/ apps/`) → temp file + `os.replace`.
3. `print()` → logger (chain/document exception); GIỮ `user_prompt` + output-method có chủ đích.

**Green:** suite xanh; `print()` sống = 0 (trừ ngoại lệ trên); export on-disk giữ nguyên. Docs: README workflow nếu CLI flags đổi.

## T11 ⚠️ — Oracle arc (rủi ro cao nhất, green-gate từng sub-step)

Main anchors: `base.py` Oracle ABC stub (get_variables:38, complete_configuration:41); `fm_oracle_model` `_base_set_c:47` / `with_configuration:121-130` / `prepare:133,189` / `_bg_data` lazy+RuntimeError:51-74 / fold:234-247; `fm_oracle.complete_configuration:116` dựng `Solver()` mỗi call:134.

- **11.0 safety-net TRƯỚC:** `tests/test_oracle_hotpath_safety_net.py` + `tests/test_prepare_task_content_safety_net.py` — pin hot-path oracle + nội dung task ConGen/QuAcq **gồm negatives** (`set_neg_tv`/`negation_map`) + fixture ConGen negative; pin thêm [#1] giá trị/thời điểm `bg_data`, [#10] kết quả `complete_configuration`, [#4] `get_c()`/Site 5.
- **11.1 [#2]:** Oracle → protocol hẹp `Membership/Catalog/Completable/BGProvider` (`conacq/oracle/base.py`); dời catalog (get_variables/feature_ids/constraint_count/next_id/fm_clauses…) xuống `FMOracleModel`; `FeatureModelOracle` mỏng = membership + facade. KHÔNG micro-class.
- **11.2 [#4]:** FMOracle purity — KHÔNG khai `base_set_c`; `prepare` set `result.set_c` (FM-only); `is_valid`/`get_c` đọc `task.set_c` cục bộ (`task.set_c + config_to_assignment_assumptions(...)` — không mutate); **xoá `with_configuration`+`dataclasses.replace` tạm của T1**; bỏ plumbing `_FMPrepResult`/`PreparationOutput`; sửa `test_oracle_model.py` (4 chỗ) + Site 5. `GenerateNE` KHÔNG sửa.
- **11.3:** oracle dùng `prepare_variable_assignments` chung (từ T5).
- **11.4:** `conacq/oracle/oracle_data.py` (mới) — **`OracleData`** frozen snapshot (tên mới, KHÔNG phải OracleTaskData) fold lên model lúc `build()`, implement `BGProvider`; `ConGenModel.prepare_task` bỏ tham số oracle; `QuAcqModel.prepare_task(task_input=None)` từ chối non-empty; [#3] `FMOracleModel.prepare_task` fail-fast `assert task_input is None`; [#1] `bg_data` **eager trong `build()`**, prepare_task pure (bỏ cache + RuntimeError thứ-tự-gọi).
- **11.5 [#10]:** `complete_configuration` giữ MỘT solver bền; per-call chỉ solve dưới assumptions. Safety-net 11.0 canh kết quả.

**Green cuối:** 4 model cùng chữ ký `prepare_task(task_input) -> PreparedTask`; model pure; `base_set_c` = 0 hit; hành vi diagnoses/membership/completion Y HỆT baseline; guard 2 chiều xanh. Docs: system-architecture oracle section + congen.md/quacq.md nếu đụng.

## T13 — Labelers + split test_diagnosis

Main: 5 file labeler (`hsdag/labeler/`); `test_diagnosis.py` 1328 LOC unittest+parameterized.

1. Template base cho labeler (gom khung lặp 4 concrete).
2. Migrate `test_diagnosis` → pytest; **tách 5 file theo thuật toán** + `tests/diagnosis_support.py`; doc twin-algorithms (cố ý tách rời).

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

## T17 — Dead-code cleanup

1. Chuyển `tests/test_bias_module.py` + `test_bias_module_1.py` → `scripts/` (demo, đổi tên `*demo*`).
2. Xoá comment cũ/field chết còn sót (ref fda29d7 + 67bfb20, **TRỪ** phần xoá dimacs).
3. ⚠️ **GIỮ `explanation/transformations/dimacs_to_configuration.py`**.

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
