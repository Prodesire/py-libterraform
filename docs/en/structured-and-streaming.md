# Plan Results and Streaming

`plan()` and `apply()` return structured results, and the streaming methods
expose Terraform output as it runs. Both build on Terraform's `-json` output.

The snippets below run against a minimal module that needs no cloud credentials
and downloads no providers:

```python
import os
import tempfile

module_dir = tempfile.mkdtemp()
with open(os.path.join(module_dir, "main.tf"), "w") as f:
    f.write(
        '''
        resource "terraform_data" "a" {
          input = "x"
        }

        output "id" {
          value = terraform_data.a.id
        }
        '''
    )

from libterraform import TerraformCommand

cli = TerraformCommand(module_dir)
cli.init(check=True)
```

## Structured results

`plan()` returns a `PlanResult` and `apply()` / `destroy()` return an
`ApplyResult`. Both are `CommandResult` subclasses, so `.retcode`, `.value` and
`.error` work exactly as before, with structured views added on top:

```python
result = cli.plan(check=True)

for change in result.changes:               # list[ResourceChange]
    print(change.address, change.action)    # terraform_data.a create

print(result.summary.add, result.summary.change, result.summary.remove)  # 1 0 0
print([o.name for o in result.outputs])     # ['id']
print(result.drift)                         # resources changed outside Terraform
```

`apply()` exposes the resources it applied and an apply summary the same way:

```python
applied = cli.apply(auto_approve=True, input=False, check=True)

print([c.address for c in applied.changes])   # ['terraform_data.a']
print(applied.summary.operation)              # apply
```

A `ResourceChange` carries `address`, `action` (Terraform's verb: `create`,
`update`, `delete`, `replace`, …), `resource_type`, `name`, `module` and
`provider`. The structured properties are empty when `json=False`; the raw text
is still in `.value`.

## Streaming output

`plan_stream()` and `apply_stream()` (and the general `stream()`) return a
`TerraformStream` that yields output while the command runs — parsed `-json`
events by default, or raw text lines with `json=False`. This keeps long
`apply` runs visible instead of waiting for the whole command to finish:

```python
with cli.apply_stream(auto_approve=True) as stream:
    for event in stream:
        if event.get("type") == "apply_complete":
            print("applied", event["hook"]["resource"]["addr"])

print(stream.retcode)
```

After iteration, `stream.retcode` and `stream.stderr` are set. Pass `check=True`
to raise `TerraformCommandError` at the end on failure. Use the stream as a
context manager (or call `close()`) to stop a long-running command early;
`cancel()` requests Terraform's cooperative shutdown explicitly.

### Async streaming

`AsyncTerraformCommand` exposes the same methods as async iterators, so an
asyncio application can consume Terraform output with `async for`:

```python
from libterraform import AsyncTerraformCommand

async_cli = AsyncTerraformCommand(module_dir)
async for event in async_cli.apply_stream(auto_approve=True):
    print(event.get("@message"))
```

Cancelling the consuming task requests cooperative cancellation of the run.

See [Results & Streaming](api/results.md) for the full API.
