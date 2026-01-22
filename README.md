# pyfect

**Structured effects for modern Python**

Python is being used to build systems far larger and more concurrent than it was originally designed for. Async is now unavoidable, yet error handling, resource management, and concurrency remain ad‑hoc and fragile. Exceptions leak everywhere. Background tasks escape. The sync/async boundary infects entire codebases.

**pyfect** exists to make this situation survivable.

It provides a small, opinionated core for describing effects explicitly, handling errors as values, and enforcing structured concurrency — without turning Python into something unrecognizable.

---

## What pyfect is

* A **Python‑native effect system** inspired by functional programming, not a port of another language
* A **single execution model** that can compose synchronous and asynchronous work
* **Explicit errors** that compose instead of exploding control flow
* **Structured concurrency by default** — no silent background work
* A **runtime‑first design** where safety is enforced at execution boundaries

pyfect favors clarity, discipline, and correctness over convenience magic.

---

## What pyfect is not

* Not a framework
* Not a replacement for `asyncio`, Trio, or AnyIO
* Not “pure FP” or academic
* Not decorator‑driven async magic
* Not a grab‑bag of monadic utilities

pyfect does not attempt to encode the entire program in types, eliminate exceptions everywhere, or abstract away Python’s runtime model.

---

## Design philosophy

### Safety over convenience

If an operation can fail, it should say so. If work runs concurrently, it should be scoped. If resources are acquired, their lifetime should be explicit.

pyfect intentionally avoids APIs that:

* spawn unscoped background tasks
* swallow errors
* rely on implicit global state
* hide sync/async boundaries

### Effects describe, runtimes decide

Effects are descriptions of work. Execution is centralized and controlled. Side effects only happen at the boundary, where they can be supervised, cancelled, logged, or traced.

### Small core, honest utilities

The core of pyfect is intentionally small. Utilities are built on top — but only when they preserve explicit failure, structured concurrency, and resource safety.

---

## Status

pyfect is in early design and exploration. The ideas and philosophy are being shaped before the implementation is finalized.

Expect breaking changes. Expect opinions. Expect discipline.

---

## License

MIT
