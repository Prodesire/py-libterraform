from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_native_bridge_registers_current_terraform_commands():
    source = (ROOT / "native" / "go" / "libterraform.go").read_text(encoding="utf-8")

    assert '"rpcapi": rpcapi.CLICommandFactory' in source
    assert '"stacks": func() (cli.Command, error)' in source
    assert "command.StacksCommand" in source
    assert 'commands["query"] = func() (cli.Command, error)' in source
    assert "command.QueryCommand" in source
