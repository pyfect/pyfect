# Runtime

Functions for executing effects and obtaining their results.

Use the `run_sync` / `run_async` variants when you are comfortable letting
errors propagate as exceptions. Use the `_exit` variants when you want to
handle errors as values using `Exit`.

::: pyfect.runtime.run_sync

::: pyfect.runtime.run_sync_exit

::: pyfect.runtime.run_async

::: pyfect.runtime.run_async_exit
