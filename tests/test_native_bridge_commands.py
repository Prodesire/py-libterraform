from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_native_bridge_registers_current_terraform_commands():
    source = (ROOT / "native" / "go" / "libterraform.go").read_text(encoding="utf-8")

    assert '"rpcapi": rpcapi.CLICommandFactory' in source
    assert '"stacks": func() (cli.Command, error)' in source
    assert "command.StacksCommand" in source
    assert 'commands["query"] = func() (cli.Command, error)' in source
    assert "command.QueryCommand" in source


def test_native_bridge_exposes_per_run_cancellation():
    source = (ROOT / "native" / "go" / "libterraform.go").read_text(encoding="utf-8")

    assert "//export RunCliWithCancel" in source
    assert "func RunCliWithCancel" in source
    assert "//export CancelCli" in source
    assert "func CancelCli" in source
    assert "cancelableRuns" in source
    assert "cancelableRun" in source
    assert "const cancelledBeforeStartExitCode = 130" in source
    assert "common shell convention for an interrupted command" in source
