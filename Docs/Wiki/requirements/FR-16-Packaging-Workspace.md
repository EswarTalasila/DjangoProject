# FR-16 Packaging Workspace (PKG) — Detailed Spec (v5 draft)

| Field | Value |
|-------|-------|
| **Status** | DRAFT |
| **Date** | 2026-03-03 |
| **Domain** | PKG |
| **Applies To** | ADMIN (system role), RESEARCHER, TEACHER |
| **Related Issues** | TBD |
| **Dependencies** | FR-03 SUDO (`EXPORT_IDENTIFIABLE`), FR-05 CRS (ownership), FR-07 ASGN, FR-08 SUB, FR-10 EXP (export datasets), FR-14 ARCH (snapshots/lifecycle), FR-11 OBS (audit/telemetry) |

---

## 1) Scope

### In Scope
- Virtual filesystem-style package builder for export artifacts.
- Saved package workspaces with folder/file tree editing.
- Node-to-dataset bindings (roster/submissions/gradebook/assignment template/assignment datasets).
- Build-time validation (permissions, row caps, size estimates, filter validity).
- Build jobs that materialize a downloadable archive (`.zip`) with user-defined tree layout.
- Build pinning to archival snapshots (`snapshotId`) or explicit live-data mode.
- Per-node anonymization/identifiable controls gated by role + sudo permissions.
- Manifest generation (`MANIFEST.json`) and file checksums (`CHECKSUMS.txt`) inside each package.
- Full audit trail for workspace mutation, validation, build, and download events.

### Out of Scope
- Public share links and external distribution workflows.
- Long-running scheduling/recurrence of package builds.
- Client-side drag-and-drop implementation details (wireframes covered separately).
- Custom scripting/transform language inside package definitions.
- Restoring archived data from package artifacts.
- Non-zip container formats in v1 (`tar`, `7z`, etc. deferred).

### Core Intent
- Bridge FR-10 exports with FR-14 archival so users can assemble reproducible, structured data packages without ad-hoc manual downloads.

---

## 2) Actors

| Role | Type | PKG domain permissions |
|------|------|------------------------|
| ADMIN | System role (`is_staff=True`) | Full workspace/build rights across all scopes, identifiable exports allowed |
| RESEARCHER | User role | Workspace/build rights across all courses; identifiable data requires `EXPORT_IDENTIFIABLE` and explicit opt-in |
| TEACHER | User role | Workspace/build rights limited to owned courses and dependent entities |

> **STUDENT excluded:** Students have no PKG access in v1.

---

## 3) User Stories

| ID | Roles | Story |
|----|-------|-------|
| PKG-US-01 | TEACHER | As a teacher I can assemble a package tree (folders/files) for my course exports so downloaded artifacts match my grading workflow. |
| PKG-US-02 | RESEARCHER | As a researcher I can build anonymized cross-course packages with reproducible filters for study pipelines. |
| PKG-US-03 | RESEARCHER | As a researcher with sudo permission I can intentionally include identifiable data in selected files. |
| PKG-US-04 | ADMIN | As an admin I can validate and build package workspaces for any scope to support audits and compliance requests. |
| PKG-US-05 | ADMIN, RESEARCHER, TEACHER | As a privileged user I can pin package builds to an archival snapshot for deterministic, reproducible outputs. |

---

## 4) Use Cases

### PKG-UC-01 — Create Workspace

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `POST /api/v1/packages/workspaces`

**Main Flow:**
1. Caller creates a workspace with name, optional description, and scope metadata.
2. System validates role access and initial scope policy.
3. System creates empty root folder node.
4. System returns workspace DTO.

**Errors:**
- `PKG-UC-01-E1`: Unauthorized role (`403`).
- `PKG-UC-01-E2`: Invalid scope (`400`).

### PKG-UC-02 — Manage Workspace Tree

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoints:**  
- `PATCH /api/v1/packages/workspaces/{workspaceId}` (rename metadata)  
- `POST /api/v1/packages/workspaces/{workspaceId}/nodes` (add node)  
- `PATCH /api/v1/packages/workspaces/{workspaceId}/nodes/{nodeId}` (rename/rebind/move)  
- `DELETE /api/v1/packages/workspaces/{workspaceId}/nodes/{nodeId}` (delete subtree)

**Main Flow:**
1. Caller edits folder/file tree and file bindings.
2. System validates tree invariants (single root, acyclic parent links, valid node types).
3. For file nodes, system validates binding schema + filter schema.
4. System persists revision and returns updated tree.

**Errors:**
- `PKG-UC-02-E1`: Workspace not found (`404`).
- `PKG-UC-02-E2`: Unauthorized mutation (`403`).
- `PKG-UC-02-E3`: Invalid tree mutation (`400`).

### PKG-UC-03 — Validate Workspace

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `POST /api/v1/packages/workspaces/{workspaceId}/validate`

**Main Flow:**
1. Caller requests preflight validation.
2. System evaluates each file node:
   - permission/scope check
   - anonymization legality
   - row/size estimate
   - snapshot availability
3. System returns `isValid`, violations, and per-node estimates.

**Errors:**
- `PKG-UC-03-E1`: Workspace not found (`404`).
- `PKG-UC-03-E2`: Unauthorized validation (`403`).

### PKG-UC-04 — Build Package Artifact

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `POST /api/v1/packages/workspaces/{workspaceId}/build`

**Query/Body Controls:**
- `snapshotId` (optional; if absent, live mode)
- `strictMode` (default true; fail all on any violating node)

**Main Flow:**
1. Caller starts a build.
2. System performs validation snapshot at job start.
3. System creates async build job.
4. Worker materializes files into virtual tree, injects `MANIFEST.json` and `CHECKSUMS.txt`.
5. Worker archives output as `.zip`, stores artifact metadata, and marks job complete.
6. Caller polls job status until complete.

**Errors:**
- `PKG-UC-04-E1`: Validation failure (`422`).
- `PKG-UC-04-E2`: Snapshot unavailable (`409`).
- `PKG-UC-04-E3`: Build exceeds package cap (`422`).

### PKG-UC-05 — Download Package Artifact

**Roles:** ADMIN, RESEARCHER, TEACHER  
**Endpoint:** `GET /api/v1/packages/artifacts/{artifactId}/download`

**Main Flow:**
1. Caller requests artifact download.
2. System validates caller can access workspace/artifact scope.
3. System returns file stream.

**Errors:**
- `PKG-UC-05-E1`: Artifact not found (`404`).
- `PKG-UC-05-E2`: Access denied (`403`).
- `PKG-UC-05-E3`: Artifact expired (`410`).

---

## 5) Constraints

### PKG-CN-01 — Node-Level Permission Enforcement
- Permission checks apply per file node, not just workspace-level.
- `identifiable=true` on a node requires `EXPORT_IDENTIFIABLE` for researchers.
- Teacher node bindings must remain within owned-course scope.

### PKG-CN-02 — Snapshot Reproducibility
- If `snapshotId` is provided, all file nodes must resolve against that immutable snapshot.
- Manifest must record `snapshotId` and effective filters for every file.

### PKG-CN-03 — Package Caps
- Global package limits enforced in validation and build:
  - `maxFileCount`
  - `maxTotalRows`
  - `maxArtifactBytes`
- Violations return `422`.

### PKG-CN-04 — Manifest and Integrity
- Every built artifact must include:
  - `MANIFEST.json` (workspace revision, snapshot/live mode, node bindings, generatedAt)
  - `CHECKSUMS.txt` (SHA-256 per file path)

### PKG-CN-05 — Audit Logging
- Log all workspace mutations, validations, builds, and downloads.
- Audit record must include actor, action, workspace, scope, anonymization flags, and outcome.

### PKG-CN-06 — Strict vs Partial Build
- `strictMode=true`: any invalid node fails entire build.
- `strictMode=false`: invalid nodes skipped and recorded in manifest warnings.

### PKG-CN-07 — Archive Compatibility
- Archived entities remain exportable only when source FR visibility policy allows it.
- Snapshot mode is preferred for archived/historical package builds.

### PKG-CN-08 — Deterministic Paths
- Package file paths are normalized and deterministic from workspace tree.
- No duplicate output paths allowed.

---

## 6) Endpoint Contract

| Method | Path | Auth | UC |
|--------|------|------|-----|
| POST | `/api/v1/packages/workspaces` | IsTeacherOrAbove | PKG-UC-01 |
| GET | `/api/v1/packages/workspaces/{workspaceId}` | IsTeacherOrAbove + scope gate | Read workspace |
| PATCH | `/api/v1/packages/workspaces/{workspaceId}` | IsTeacherOrAbove + scope gate | PKG-UC-02 |
| POST | `/api/v1/packages/workspaces/{workspaceId}/nodes` | IsTeacherOrAbove + scope gate | PKG-UC-02 |
| PATCH | `/api/v1/packages/workspaces/{workspaceId}/nodes/{nodeId}` | IsTeacherOrAbove + scope gate | PKG-UC-02 |
| DELETE | `/api/v1/packages/workspaces/{workspaceId}/nodes/{nodeId}` | IsTeacherOrAbove + scope gate | PKG-UC-02 |
| POST | `/api/v1/packages/workspaces/{workspaceId}/validate` | IsTeacherOrAbove + scope gate | PKG-UC-03 |
| POST | `/api/v1/packages/workspaces/{workspaceId}/build` | IsTeacherOrAbove + scope gate | PKG-UC-04 |
| GET | `/api/v1/packages/jobs/{jobId}` | IsTeacherOrAbove + scope gate | Job status |
| GET | `/api/v1/packages/artifacts/{artifactId}/download` | IsTeacherOrAbove + scope gate | PKG-UC-05 |

---

## 7) Error Model

Standard payload:
- `{"detail": "<message>"}`

Expected statuses:
- `200`: successful read/download
- `201`: workspace created
- `202`: build accepted/job created
- `400`: invalid input/tree mutation/filter schema
- `401`: unauthenticated
- `403`: role/scope/permission violation
- `404`: workspace/node/job/artifact not found
- `409`: snapshot or archival-state conflict
- `410`: artifact expired
- `422`: validation or size/cap constraint failure

---

## 8) Test Strategy by Layer

### Backend Unit
- Tree validation (acyclic, unique paths, valid node types).
- Node binding validation and permission checks.
- Manifest/checksum generation.
- Strict vs partial build behavior.

### Backend Integration
- Role/scope gates for teacher/researcher/admin.
- Researcher identifiable export permission enforcement.
- Snapshot pinning and reproducibility assertions.
- Build job lifecycle and download authorization.
- Audit log creation on mutate/validate/build/download.

### Frontend Unit/Integration (deferred to UI phase)
- Workspace tree interactions.
- Node binding forms and validation surfaces.
- Build status polling and artifact download UX.

### System Tests
- End-to-end package generation with mixed file nodes.
- Archived snapshot package reproducibility.
- Cross-role access control.

---

## 9) NFR Cross-References

- **NFR-Security:** node-level authorization, strict scope enforcement, expiring artifacts.
- **NFR-Privacy:** anonymization defaults, explicit opt-in for identifiable output.
- **NFR-Reliability:** deterministic build manifests, reproducible snapshot builds.
- **NFR-Performance:** async build workers, capped workloads, streaming artifact delivery.
- **NFR-Maintainability:** workspace and build services isolated from export source adapters.

---

## 10) Cross-Domain References

| FR | Reference | Notes |
|----|-----------|-------|
| FR-10 EXP | Export adapters | PKG file nodes consume EXP export datasets and filters. |
| FR-14 ARCH | Snapshot pinning | PKG supports deterministic historical builds via `snapshotId`. |
| FR-03 SUDO | `EXPORT_IDENTIFIABLE` | Governs identifiable researcher outputs at node level. |
| FR-05 CRS | Ownership gate | Teacher workspace scope restricted to owned courses. |
| FR-07 ASGN / FR-08 SUB | Assignment/submission rows | File bindings pull assignment/submission data for package nodes. |

---

## 11) Current Implementation Alignment Notes

Current implementation has a functional PKG backend baseline with workspace CRUD, node management, validation, build, and download flows.

Implemented alignment:
1. **PKG domain models implemented.** `PackageWorkspace`, `PackageNode`, `PackageBuildJob`, `PackageArtifact`, and `PackageAuditLog` exist with initial migration.
2. **API surface implemented.** Workspace create/get/update, node add/update/delete, validate, build, job status, and artifact download endpoints are wired under `/api/v1/packages/`.
3. **Validation engine implemented.** Tree structure checks, per-node binding checks, role/scope checks, deterministic path checks, and core cap checks are enforced.
4. **Build pipeline implemented.** Build materializes node-bound CSVs via export services and injects `MANIFEST.json` + `CHECKSUMS.txt` into a `.zip` artifact.
5. **Role/scope control implemented.** Teacher scope is course ownership constrained; researcher identifiable exports require `EXPORT_IDENTIFIABLE`.
6. **Integration coverage implemented.** FR-traceable integration tests for PKG UC/CN scenarios are present and passing.

Known deferreds / follow-ups:
1. **Async execution deferred.** Build currently runs synchronously in request flow; queue/worker execution remains future work.
2. **Snapshot store integration deferred.** Snapshot validation currently uses a placeholder check and does not yet bind to FR-14 snapshot persistence.
3. **Full row/byte caps deferred.** File-count cap is enforced; row/byte cap enforcement needs deeper preflight estimation integration.
4. **Artifact GC deferred.** Expired artifacts are blocked at download time but not yet garbage-collected from disk.
5. **Frontend workspace UI deferred.** Backend is available; PKG UX builder remains a separate frontend phase.
