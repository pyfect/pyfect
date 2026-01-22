# Contributing to pyfect

Thanks for your interest in contributing to pyfect.

pyfect is an opinionated project. Contributions are welcome — but only if they align with the project’s core philosophy: **explicitness, safety, and disciplined execution**.

---

## Guiding principles

When proposing changes or additions, keep these rules in mind:

* **No hidden side effects**
* **No silent concurrency**
* **No swallowed errors**
* **No implicit global state**

If a contribution makes code *shorter* but also *more dangerous*, it will likely be rejected.

---

## Scope

The core of pyfect is intentionally small.

Please avoid proposing:

* large abstractions in the core
* convenience helpers that obscure failure or concurrency
* decorator‑driven magic
* APIs that require deep runtime introspection

Utilities and extensions should be layered on top of the core and must preserve its guarantees.

---

## Process

* Open an issue before submitting large changes
* Be explicit about trade‑offs
* Prefer clarity over cleverness
* Expect discussion — design matters here

---

## Code of conduct

This project follows the Code of Conduct defined in `CODE_OF_CONDUCT.md`.

Be respectful. Be constructive. Assume good faith.
