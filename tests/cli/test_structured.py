import pytest

from libterraform import (
    ApplyResult,
    ChangeSummary,
    CommandResult,
    PlanResult,
    ResourceChange,
    TerraformCommand,
)
from libterraform.models import (
    parse_applied_changes,
    parse_drift,
    parse_output_changes,
    parse_planned_changes,
    parse_summary,
)

DATA_MODULE = """
resource "terraform_data" "a" {
  input = "x"
}

resource "terraform_data" "b" {
  input = "y"
}

output "id_a" {
  value = terraform_data.a.id
}
"""


@pytest.fixture
def data_cli(tmp_path):
    module = tmp_path / "data"
    module.mkdir()
    (module / "main.tf").write_text(DATA_MODULE)
    cli = TerraformCommand(str(module))
    cli.init(check=True)
    return cli


# --- parser unit tests (synthetic events, no Terraform required) ---


def test_parse_planned_changes_extracts_address_and_action():
    events = [
        {"type": "version"},
        {
            "type": "planned_change",
            "change": {
                "resource": {
                    "addr": "terraform_data.a",
                    "resource_type": "terraform_data",
                    "resource_name": "a",
                    "module": "",
                    "implied_provider": "terraform",
                },
                "action": "create",
            },
        },
    ]

    changes = parse_planned_changes(events)

    assert changes == [
        ResourceChange(
            address="terraform_data.a",
            action="create",
            resource_type="terraform_data",
            name="a",
            module="",
            provider="terraform",
        )
    ]


def test_parse_applied_changes_reads_hook():
    events = [
        {
            "type": "apply_complete",
            "hook": {
                "resource": {
                    "addr": "terraform_data.a",
                    "resource_type": "terraform_data",
                },
                "action": "create",
            },
        }
    ]

    changes = parse_applied_changes(events)

    assert changes[0].address == "terraform_data.a"
    assert changes[0].action == "create"


def test_parse_drift_reads_resource_drift_events():
    events = [
        {
            "type": "resource_drift",
            "change": {
                "resource": {"addr": "terraform_data.a"},
                "action": "update",
            },
        }
    ]

    drift = parse_drift(events)

    assert drift[0].address == "terraform_data.a"
    assert drift[0].action == "update"


def test_parse_summary_filters_by_operation():
    events = [
        {"type": "change_summary", "changes": {"add": 2, "operation": "plan"}},
        {"type": "change_summary", "changes": {"add": 2, "operation": "apply"}},
    ]

    assert parse_summary(events, operation="plan") == ChangeSummary(
        add=2, operation="plan"
    )
    assert parse_summary(events, operation="apply").operation == "apply"


def test_parse_summary_maps_import_keyword():
    events = [{"type": "change_summary", "changes": {"import": 3, "operation": "plan"}}]

    assert parse_summary(events).import_ == 3


def test_parse_output_changes_uses_last_outputs_event():
    events = [
        {
            "type": "outputs",
            "outputs": {"id_a": {"action": "create", "sensitive": False}},
        },
    ]

    outputs = parse_output_changes(events)

    assert outputs[0].name == "id_a"
    assert outputs[0].action == "create"
    assert outputs[0].sensitive is False


def test_parsers_tolerate_non_list_value():
    # json=False yields a plain string; parsers must return empty, not raise.
    assert parse_planned_changes("Plan: 1 to add") == []
    assert parse_summary("text") == ChangeSummary()
    assert parse_output_changes(None) == []


# --- integration tests against real Terraform output ---


def test_plan_returns_plan_result_with_changes(data_cli):
    result = data_cli.plan(check=True)

    assert isinstance(result, PlanResult)
    assert isinstance(result, CommandResult)  # backward compatible
    addresses = {c.address for c in result.changes}
    assert addresses == {"terraform_data.a", "terraform_data.b"}
    assert all(c.action == "create" for c in result.changes)
    assert result.summary.add == 2
    assert result.summary.change == 0
    assert {o.name for o in result.outputs} == {"id_a"}
    assert result.drift == []


def test_apply_returns_apply_result_with_changes(data_cli):
    result = data_cli.apply(auto_approve=True, input=False, check=True)

    assert isinstance(result, ApplyResult)
    addresses = {c.address for c in result.changes}
    assert addresses == {"terraform_data.a", "terraform_data.b"}
    assert result.summary.operation == "apply"
    assert result.summary.add == 2


def test_structured_properties_empty_when_not_json(data_cli):
    result = data_cli.plan(json=False)

    assert isinstance(result, PlanResult)
    assert isinstance(result.value, str)
    assert result.changes == []
    assert result.summary == ChangeSummary()


def test_plan_result_is_picklable_with_structured_access(data_cli):
    import pickle

    result = data_cli.plan(check=True)
    restored = pickle.loads(pickle.dumps(result))

    assert isinstance(restored, PlanResult)
    assert {c.address for c in restored.changes} == {
        "terraform_data.a",
        "terraform_data.b",
    }


def test_repr_distinguishes_result_types(data_cli):
    assert "PlanResult" in repr(data_cli.plan(check=True))
