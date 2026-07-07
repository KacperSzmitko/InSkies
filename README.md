# InSkies

InSkies is an astrophotography editing platform built around collaborative, explainable workflows. Users create projects, edit images in ordered steps, and publish results together with the full history of operations so other users can learn how a given image was achieved.

This document captures the agreed architecture for the project so implementation can follow a clear model instead of growing ad hoc.

## Product Goals

- Let users manage astrophotography projects end to end.
- Support step-based image editing rather than opaque final results.
- Preserve edit history so workflows are reproducible and reviewable.
- Separate user-facing APIs from compute-heavy processing.
- Allow future AI agents to use the editing system through the same controlled contracts as normal users.

## Architecture

The project is modeled as two backend runtime parts, not three:

1. `main backend` - one FastAPI application that owns users, projects, comments, likes, editing orchestration, edit history, and job scheduling.
2. `operator` - a worker-oriented component that performs heavy image-processing operations.
3. `frontend` - the web UI.
4. `db` - shared database models, migrations, and database integration utilities.

Projects support public viewing, comments, and likes from other users. They do not support collaborative editing.

## High-Level Architecture

```text
Frontend
  |
  v
Main Backend (FastAPI)
  |
  +----------------------------+
  |                            |
  v                            v
Shared Database           Outbox Dispatcher
  |                            |
  |                            v
  |                      Queue / Task Broker
  |                            |
  |                            v
  +--------------------> Operator Workers
                               |
                               v
                         S3 / Object Storage
```

## Component Responsibilities

### `src/backend/app`

The main backend owns:

- authentication and user accounts
- projects and publishing state
- comments, likes, and community features
- editing orchestration and validation
- edit history and current project state
- scheduling processing jobs for the operator
- reporting job status back to the UI

This component is the control plane of the system. It decides what work should be executed and how that work fits into project history, but it should not perform heavy image processing itself.

### `src/backend/operator`

The operator owns execution of compute-heavy workloads:

- calibration and preprocessing tasks
- stacking, denoising, stretching, color correction, and export tasks
- CPU- or GPU-heavy operations
- artifact generation and writes to object storage

The operator should be stateless from an application perspective. It should know about jobs, operations, artifacts, and results, but not broader product concerns such as comments, likes, permissions, or presentation logic.

### `src/backend/db`

The shared database package owns infrastructure concerns:

- SQLAlchemy models
- Alembic migrations
- engine and session setup
- repository-facing database interfaces and utilities

It should not become a shared business-logic layer.

### `src/frontend`

The frontend owns:

- authentication flows
- project browsing and community interactions
- editing screens and step history visualization
- job-progress feedback for long-running processing

## Architectural Principles

### 1. Main backend and operator are the only hard runtime boundary

The operator is isolated because it has different scaling, infrastructure, and failure characteristics.

The user-facing backend and editing orchestration stay in the same deployment unit.

### 2. Use one database with ownership boundaries

One relational database simplifies development, migrations, and consistency.

Ownership model:

- user and community data belong to the main backend domain
- workflow and edit-history data belong to the main backend domain
- operator-related execution records are still owned logically by the main backend domain, even if the operator writes status and results
- `db` provides schema and plumbing, not cross-cutting business behavior

### 3. Treat edit history as a core product model, not an audit log

For InSkies, history is part of the product value. Users are not only producing final images. They are also producing a learnable workflow.

Edit history is modeled as immutable operations with explicit inputs, outputs, parameters, authorship, and timestamps.

Project rules:

- store immutable edit steps as the source of truth
- optionally materialize a "current project state" for faster reads
- keep enough metadata to explain and replay workflows later
- keep history strictly linear for now

### 4. Keep processing tasks scoped to a single operation

One background task maps to one editing operation.

Benefits:

- simpler validation
- clearer retries
- better lineage tracking
- better observability
- easier future composition into multi-step workflows
- a cleaner future interface for AI agents

Examples:

- apply denoise
- run background extraction
- stretch histogram
- export preview

### 5. Store large files in object storage, not the database

Source images, intermediate outputs, previews, masks, and exports live in S3 or equivalent object storage.

The database should store:

- artifact metadata
- storage keys or URLs
- dimensions, format, and checksums
- relationships between artifacts and edit steps
- provenance information

## Background Jobs, Retries, and Reliability

### Why retries matter

Background systems are usually at-least-once delivery systems. That means duplicate execution is normal unless you explicitly design around it.

Common failure scenarios:

- the backend commits DB state but fails before publishing a task
- the broker redelivers a message after a timeout
- a worker finishes work but crashes before acknowledging success
- a network or storage dependency fails temporarily and the task is retried

Because of that, retries should be considered part of the architecture, not an edge case.

### Separate intent from execution

The user-visible operation and the infrastructure execution attempt are different concepts.

Domain distinction:

- `EditStep` = the user-visible intent to apply an operation
- `ProcessingJob` = the schedulable execution record for that step
- `JobAttempt` = one actual worker attempt to execute the job

Why this matters:

- one logical step may be retried multiple times
- retries should not rewrite user history
- infrastructure failures should be diagnosable separately from workflow intent

### Idempotency requirement

The operator side should assume the same job message can arrive more than once.

That means execution should be idempotent or at least duplicate-safe:

- a job should have a stable identity
- the worker should be able to detect an already completed job
- repeated delivery should not corrupt history
- output handling should avoid inconsistent duplicates where possible

The queue gives you at-least-once delivery. The application must make repeated delivery harmless.

## Outbox Pattern

### Problem the outbox solves

The main backend needs to do two things when a user requests an operation:

1. save domain state in the database
2. publish work to the task broker

Those are two different systems. They do not commit atomically.

Without an outbox, a failure can leave the system inconsistent.

Example:

1. create `EditStep`
2. create `ProcessingJob`
3. try to publish task
4. broker publish fails

Now the step exists, but no worker will ever process it.

### Basic idea

The outbox is a durable handoff table inside the same relational database.

Instead of publishing directly inside the request flow, the main backend does this in one DB transaction:

1. create `EditStep`
2. create `ProcessingJob`
3. insert an `OutboxEvent`
4. commit

Then a separate dispatcher process reads unsent outbox rows and publishes them to the broker.

If the publish succeeds, the dispatcher marks the outbox row as sent.

This means the system does not depend on "DB write and broker publish both succeed right now." It depends on the safer guarantee that "if the transaction commits, the intent to publish is durably stored."

### What the outbox is and is not

The outbox is:

- a durable record of pending integration messages
- a bridge between database state and async dispatch
- a reliability mechanism

The outbox is not:

- the main workflow engine
- the source of truth for edits or jobs
- a replacement for idempotent workers

Domain state should remain in domain tables such as `EditStep` and `ProcessingJob`.

### Outbox data

An outbox row includes:

- `id`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `payload` as JSON
- `created_at`
- `published_at` or status
- `attempt_count`
- `last_error`

Example event meaning:

- `processing_job.created`

### Flow

Request flow:

1. user requests an operation such as denoise
2. backend validates project state and parameters
3. backend creates `EditStep`, `ProcessingJob`, and `OutboxEvent` in one DB transaction
4. transaction commits

Dispatch flow:

1. dispatcher reads unsent outbox rows
2. dispatcher publishes the queue message
3. dispatcher marks the outbox row as published

Execution flow:

1. operator receives job message
2. operator loads the job
3. operator creates a `JobAttempt`
4. operator executes the single operation
5. operator writes output artifacts and metadata
6. operator marks the job as succeeded or failed

### Cost and complexity tradeoff

For this project, a simple outbox is part of the architecture.

Infrastructure cost should be low:

- one extra table
- one lightweight polling dispatcher
- a few extra inserts and updates

The real cost is engineering complexity, not AWS bill.

For InSkies, that tradeoff is usually justified because image-editing jobs are core product behavior, not disposable side effects.

Implementation scope:

- keep the outbox implementation simple
- use a polling dispatcher rather than a heavy event platform
- avoid overbuilding beyond the reliability actually needed

## Artifacts and Provenance

Artifacts are first-class domain entities, not just files in S3.

In this product, the files are the actual substance of the workflow. They are not generic attachments.

Artifact categories include:

- raw light frames
- darks, flats, and bias frames
- calibrated outputs
- aligned or stacked outputs
- masks
- previews
- intermediate operation outputs
- final exports

Each artifact should carry domain meaning such as:

- what kind of artifact it is
- which project it belongs to
- who created it
- which operation produced it
- which input artifacts were used
- whether it is intermediate, preview, current, or final

This is provenance: the lineage of an output.

Why provenance matters:

- reproducibility
- educational value for other users
- debugging failed or surprising outputs
- future AI-agent planning
- caching and deduplication opportunities
- support for comparing alternate editing paths later

Modeling direction:

- `Artifact` for stored domain files and image objects
- explicit step input and output relationships
- `OperationDefinition` for operation type and version metadata
- `EditStep` for user-visible operation intent

The main point is that the system should be able to explain how a final image was produced through structured lineage, not inferred filenames.

## Future AI Agent Integration

The long-term plan is to let LLM-based agents use the editing system as tools to achieve a desired effect.

That works well with the current architectural decisions if the agent is treated as a planner, not as a bypass around the platform.

Rules for agent integration:

- the agent should call the same backend tools or APIs as a normal client
- the backend should still validate allowed operations and parameters
- the backend should still create normal `EditStep`, `ProcessingJob`, and history records
- the operator should not care whether the request came from a human or an agent

This keeps the system auditable, explainable, and safe.

Single-operation tasks are a good foundation for this because agents can compose multiple operations while each individual step remains explicit and traceable.

## Technology Direction

### Backend

- Python
- FastAPI for the main backend
- SQLAlchemy for ORM and database access
- Alembic for migrations
- Taskiq for background tasks

### Infrastructure

- AWS for deployment
- EC2 for heavy operator workers
- S3 for source images and generated artifacts
- a managed queue or broker depending on task framework choice
- one relational database shared by the backend and operator infrastructure

### Frontend

The repository already separates `src/frontend`, so the UI can evolve independently from the backend. The editing UX uses:

- timeline visualization
- job-progress polling initially
- websocket-based updates later
- large-image preview handling
- clear distinction between draft and published project states

## Background Task System

The project uses Taskiq for background processing.

Reasons:

- async-first design fits the backend direction
- lighter fit for a modern FastAPI-based codebase
- single-operation job model keeps the task layer straightforward

Tradeoff:

- smaller ecosystem than Celery

## Proposed Core Domain Concepts

The domain model includes:

- `User`
- `Project`
- `Comment`
- `Like`
- `Artifact`
- `EditStep`
- `OperationDefinition`
- `ProcessingJob`
- `JobAttempt`
- `OutboxEvent`

Modeling rules:

- separate logical edit steps from execution jobs and attempts
- model artifact lineage explicitly
- version operations so reproducibility does not drift as implementations evolve

## Suggested Repository Shape

Current structure:

```text
src/
  backend/
    app/
    db/
      models.py
    editor/
    operator/
  frontend/
```

Repository direction:

```text
src/
  backend/
    app/
      api/
      services/
      repositories/
      schemas/
      outbox/
    operator/
      workers/
      operations/
      storage/
    db/
      models/
      migrations/
      session.py
      interfaces/
  frontend/
```

The existing `editor` directory can be retired later or repurposed as an internal module inside the main backend. The runtime architecture assumes one main backend and one operator.

## Key Risks To Handle Early

- unclear ownership boundaries in the shared database
- modeling edit history too weakly and losing replayability
- mixing domain workflow state with infrastructure retry state
- storing artifact data without proper provenance and lineage
- allowing operator code to absorb application-level concerns
- underestimating duplicate delivery and retry behavior in background systems
- rebuilding current project state from long histories becoming too slow

## Initial Architectural Decisions

These are the agreed architectural decisions for the project:

1. Use one main FastAPI backend instead of splitting `app` and `editor` deployments early.
2. Keep `operator` as an isolated worker-oriented component.
3. Use one relational database initially, but enforce domain ownership discipline.
4. Store image artifacts in S3, not in the database.
5. Treat edit history as a product feature and model it as immutable operations.
6. Keep background tasks scoped to a single operation.
7. Separate logical edit steps from processing jobs and job attempts.
8. Use an outbox pattern for reliable DB-to-broker dispatch.
9. Treat artifacts and provenance as first-class domain entities.
10. Keep shared code in `db` infrastructure-focused rather than business-logic-heavy.
11. Do not support collaborative editing.
12. Keep edit history strictly linear.
13. Use polling for job updates initially and websockets later.
14. Use Taskiq as the background task system.

## Discussion Summary

The overall architecture is sound if it stays focused on the real complexity: workflow correctness, artifact lineage, and reliable compute orchestration.

The agreed shape for the current stage is:

- one main backend for product and orchestration concerns
- one isolated operator layer for heavy execution
- one shared relational database with clear ownership rules
- one simple outbox for reliable task dispatch
- one explicit artifact and provenance model as a core part of the domain
- one linear edit history
- one polling-first update model with websockets later
- one Taskiq-based background execution layer

If those decisions stay disciplined, the system can remain relatively simple while still supporting future scale and future AI-agent driven workflows.