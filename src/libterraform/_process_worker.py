"""Private subprocess entry point for process-isolated Terraform execution."""

import pickle
import sys

from libterraform.cli import _invoke_cli, _run_argv_in_process


def _read_payload():
    return pickle.loads(sys.stdin.buffer.read())


def _run_command(response_path):
    payload = _read_payload()
    try:
        response = ("ok", _run_argv_in_process(payload["argv"], check=False))
    except BaseException as exc:
        response = ("error", exc)
    with open(response_path, "wb") as f:
        pickle.dump(response, f, protocol=pickle.HIGHEST_PROTOCOL)
    return 0


def _stream_command(run_id):
    payload = _read_payload()
    return _invoke_cli(
        payload["argv"],
        sys.stdout.fileno(),
        sys.stderr.fileno(),
        run_id,
    )


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m libterraform._process_worker MODE ...")
    mode = sys.argv[1]
    if mode == "run":
        if len(sys.argv) != 3:
            raise SystemExit(
                "usage: python -m libterraform._process_worker run RESPONSE"
            )
        return _run_command(sys.argv[2])
    if mode == "stream":
        if len(sys.argv) != 3:
            raise SystemExit(
                "usage: python -m libterraform._process_worker stream RUN_ID"
            )
        return _stream_command(sys.argv[2])
    raise SystemExit(f"unknown libterraform worker mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
