import os
import uuid
from contextvars import ContextVar
from ctypes import POINTER, c_char_p, c_int, c_int64
from threading import Thread
from typing import List, Optional, Sequence, Tuple, Union

from libterraform import _lib_tf
from libterraform.common import WINDOWS, CmdType, json_loads
from libterraform.exceptions import TerraformCommandError, TerraformFdReadError
from libterraform.models import (
    ChangeSummary,
    OutputChange,
    ResourceChange,
    parse_applied_changes,
    parse_drift,
    parse_output_changes,
    parse_planned_changes,
    parse_summary,
)

_run_cli = _lib_tf.RunCli
_run_cli.argtypes = [c_int64, POINTER(c_char_p), c_int64, c_int64]
_run_cli_with_cancel = getattr(_lib_tf, "RunCliWithCancel", None)
if _run_cli_with_cancel is not None:
    _run_cli_with_cancel.argtypes = [
        c_char_p,
        c_int64,
        POINTER(c_char_p),
        c_int64,
        c_int64,
    ]
_cancel_cli = getattr(_lib_tf, "CancelCli", None)
if _cancel_cli is not None:
    _cancel_cli.argtypes = [c_char_p]
    _cancel_cli.restype = c_int

_current_run_id: ContextVar[Optional[str]] = ContextVar(
    "libterraform_current_run_id",
    default=None,
)


def _cancel_cli_run(run_id: str) -> int:
    if not run_id or _cancel_cli is None:
        return 0
    return _cancel_cli(run_id.encode("utf-8"))


def flag(value):
    return ... if value else None


def _build_argv(cmd, args=None, options=None, chdir=None, json=False):
    """Build the Terraform argv list from a command, args and options.

    Option keys are snake_case and converted to ``-dash-case``. Values convert
    as: ``...`` -> value-less flag, ``bool`` -> lowercase, ``list`` -> repeated
    flag, ``dict`` -> repeated ``-flag=key=value``. ``None`` values are skipped.
    """
    argv = []
    if chdir:
        argv.append(f"-chdir={chdir}")
    if isinstance(cmd, (list, tuple)):
        argv.extend(cmd)
    else:
        argv.append(cmd)
    options = dict(options) if options else {}
    if json:
        options.update(json=flag(json))
    for option, value in options.items():
        if value is None:
            continue
        if "_" in option:
            option = option.replace("_", "-")
        if value is ...:
            argv += [f"-{option}"]
            continue
        if isinstance(value, list):
            argv += [f"-{option}={val}" for val in value]
            continue
        if isinstance(value, dict):
            argv += [f"-{option}={k}={v}" for k, v in value.items()]
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        argv += [f"-{option}={value}"]
    if args:
        argv.extend(args)
    return argv


def _invoke_cli(argv, w_stdout_fd, w_stderr_fd, run_id=None):
    """Call into the shared library, writing stdout/stderr to the given fds.

    Blocks until the command completes and returns its exit code. When ``run_id``
    is set and the cancel-aware entry point is available, the run is registered
    so `_cancel_cli_run` can interrupt it.
    """
    argc = len(argv)
    c_argv = (c_char_p * argc)()
    c_argv[:] = [arg.encode("utf-8") for arg in argv]
    if WINDOWS:
        import msvcrt

        w_stdout = msvcrt.get_osfhandle(w_stdout_fd)
        w_stderr = msvcrt.get_osfhandle(w_stderr_fd)
    else:
        w_stdout = w_stdout_fd
        w_stderr = w_stderr_fd
    if run_id and _run_cli_with_cancel is not None:
        return _run_cli_with_cancel(
            run_id.encode("utf-8"), argc, c_argv, w_stdout, w_stderr
        )
    return _run_cli(argc, c_argv, w_stdout, w_stderr)


def _drain_fd(fd):
    """Read a file descriptor to EOF and return its text."""
    with os.fdopen(fd, encoding="utf-8") as f:
        return f.read()


def _merge_var_options(options, vars, var_files):
    """Map the high-level ``vars``/``var_files`` kwargs to ``-var``/``-var-file``."""
    if vars is not None:
        options["var"] = vars
    if var_files is not None:
        options["var_file"] = var_files


# Streaming methods return a TerraformStream (an iterator, not a value), so they
# are handled specially by the async wrapper and excluded from the process pool
# (a live stream cannot cross a process boundary).
_STREAM_METHODS = frozenset({"stream", "plan_stream", "apply_stream"})


class CommandResult:
    __slots__ = ("retcode", "value", "error", "json")

    def __init__(self, retcode, value, error=None, json=False):
        self.retcode = retcode
        self.value = value
        self.error = error
        self.json = json

    def __repr__(self):
        return f"<CommandResult retcode={self.retcode!r} json={self.json!r}>"


class PlanResult(CommandResult):
    """Result of `plan()`.

    Adds structured, lazily-parsed views over the ``-json`` output. The
    structured properties are empty when ``json=False`` was used. ``value`` still
    holds the raw parsed events, exactly like a plain `CommandResult`.
    """

    __slots__ = ()

    @property
    def changes(self) -> List[ResourceChange]:
        """Resources the plan would change, as `ResourceChange` items."""
        return parse_planned_changes(self.value)

    @property
    def drift(self) -> List[ResourceChange]:
        """Resources that have drifted from the recorded state."""
        return parse_drift(self.value)

    @property
    def summary(self) -> ChangeSummary:
        """Add / change / remove / import counts for the plan."""
        return parse_summary(self.value, operation="plan")

    @property
    def outputs(self) -> List[OutputChange]:
        """Planned changes to root module outputs."""
        return parse_output_changes(self.value)

    def __repr__(self):
        return f"<PlanResult retcode={self.retcode!r} json={self.json!r}>"


class ApplyResult(CommandResult):
    """Result of `apply()` and `destroy()`.

    Adds structured, lazily-parsed views over the ``-json`` output. The
    structured properties are empty when ``json=False`` was used.
    """

    __slots__ = ()

    @property
    def changes(self) -> List[ResourceChange]:
        """Resources that were applied, as `ResourceChange` items."""
        return parse_applied_changes(self.value)

    @property
    def summary(self) -> ChangeSummary:
        """Add / change / remove / import counts for the apply."""
        return parse_summary(self.value, operation="apply")

    @property
    def outputs(self) -> List[OutputChange]:
        """Changes to root module outputs."""
        return parse_output_changes(self.value)

    def __repr__(self):
        return f"<ApplyResult retcode={self.retcode!r} json={self.json!r}>"


class TerraformStream:
    """Streaming view over a running Terraform command.

    Iterating yields output as the command produces it: parsed ``-json`` events
    when ``json=True`` (the default), or raw text lines otherwise. The command
    runs in a background thread, so the event loop / caller sees output live
    instead of waiting for the command to finish.

    After iteration completes, `retcode` and `stderr` are populated.
    If ``check=True`` and the command failed, iteration raises
    `TerraformCommandError` at the end. Use it as
    a context manager (or call `close()`) to stop a long-running command
    early; `cancel()` requests cooperative cancellation explicitly.

    Example::

        with cli.apply_stream(auto_approve=True) as stream:
            for event in stream:
                print(event.get("@message"))
        print(stream.retcode)
    """

    def __init__(self, argv, json=True, check=False):
        self._argv = argv
        self._json = json
        self._check = check
        self._run_id = uuid.uuid4().hex
        self.retcode: Optional[int] = None
        self.stderr: Optional[str] = None
        self._started = False
        self._closed = False
        self._f = None
        self._stderr_result: list = []
        self._cli_thread: Optional[Thread] = None
        self._stderr_thread: Optional[Thread] = None

    def __iter__(self) -> "TerraformStream":
        return self

    def __next__(self):
        if not self._started:
            self._start()
        if self._closed:
            raise StopIteration
        assert self._f is not None
        while True:
            line = self._f.readline()
            if not line:
                self._finish()
                raise StopIteration
            line = line.rstrip("\n")
            if self._json:
                if not line:
                    continue
                return json_loads(line)
            return line

    def _start(self):
        self._started = True
        r_stdout_fd, w_stdout_fd = os.pipe()
        r_stderr_fd, w_stderr_fd = os.pipe()
        self._f = os.fdopen(r_stdout_fd, encoding="utf-8")
        self._stderr_thread = Thread(
            target=lambda: self._stderr_result.append(_drain_fd(r_stderr_fd)),
            daemon=True,
        )
        self._stderr_thread.start()
        self._cli_thread = Thread(
            target=self._run, args=(w_stdout_fd, w_stderr_fd), daemon=True
        )
        self._cli_thread.start()

    def _run(self, w_stdout_fd, w_stderr_fd):
        self.retcode = _invoke_cli(self._argv, w_stdout_fd, w_stderr_fd, self._run_id)

    def _join(self):
        assert self._cli_thread is not None and self._stderr_thread is not None
        self._cli_thread.join()
        self._stderr_thread.join()
        self.stderr = self._stderr_result[0] if self._stderr_result else ""
        if self._f is not None:
            try:
                self._f.close()
            except OSError:
                pass

    def _finish(self):
        if self._closed:
            return
        self._closed = True
        self._join()
        if self._check and self.retcode not in (0, 2):
            raise TerraformCommandError(self.retcode, self._argv, "", self.stderr)

    def cancel(self):
        """Request cooperative cancellation of the running command."""
        _cancel_cli_run(self._run_id)

    def close(self):
        """Stop the command if still running and release resources."""
        if not self._started or self._closed:
            self._closed = True
            return
        self.cancel()
        # Drain remaining output so the worker can exit, then join.
        assert self._f is not None
        try:
            while self._f.readline():
                pass
        except (OSError, ValueError):
            pass
        self._closed = True
        self._join()

    def __enter__(self) -> "TerraformStream":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False


class TerraformCommand:
    """Terraform command line.

    https://developer.hashicorp.com/terraform
    """

    def __init__(self, cwd=None):
        self.cwd = cwd

    @classmethod
    def run(
        cls,
        cmd: CmdType,
        args: Optional[Sequence[str]] = None,
        options: Optional[dict] = None,
        chdir=None,
        check: bool = False,
        json=False,
    ) -> Tuple[int, str, str]:
        """
        Run command with args and return a tuple (retcode, stdout, stderr).

        The returned object will have attributes retcode, value, json.

        If check is True and the return code was non 0 or 2, it raises a
        TerraformCommandError. The TerraformCommandError object will have the return code
        in the retcode attribute, and stdout & stderr attributes.

        :param cmd: Terraform command
        :param args: Terraform command argument list
        :param options: Terraform command options
            Each key in options should be snake format, and will be convert to command option key automatically.
                ex. no_color will be converted to -no-color.
            Each value in options will be converted to appropriate command value automatically.
            The conversion rules for values are as follows:
                value ... will be regarded as flag option.
                    ex. {"json": ...} -> -json
                boolean value will be converted to lower boolean.
                    ex. {"backend": True} -> -backend=true
                list value will be converted to multi pairs.
                    ex. {"var": ["Name1=xx", "Name2=xx"]} -> -var Name1=xx -var Name2=xx
        :param chdir: Switch to a different working directory before executing the given subcommand.
        :param check: Whether to check return code.
        :param json: Whether to load stdout as json. Only partial commands support json param.
        :return: Command result tuple (retcode, stdout, stderr).
        """
        argv = _build_argv(cmd, args, options, chdir, json)
        r_stdout_fd, w_stdout_fd = os.pipe()
        r_stderr_fd, w_stderr_fd = os.pipe()

        stdout_buffer = []
        stderr_buffer = []
        stdout_thread = Thread(target=cls._fdread, args=(r_stdout_fd, stdout_buffer))
        stdout_thread.daemon = True
        stdout_thread.start()
        stderr_thread = Thread(target=cls._fdread, args=(r_stderr_fd, stderr_buffer))
        stderr_thread.daemon = True
        stderr_thread.start()

        retcode = _invoke_cli(argv, w_stdout_fd, w_stderr_fd, _current_run_id.get())

        stdout_thread.join()
        stderr_thread.join()
        if not stdout_buffer:
            raise TerraformFdReadError(fd=r_stdout_fd)
        if not stderr_buffer:
            raise TerraformFdReadError(fd=r_stderr_fd)
        stdout = stdout_buffer[0]
        stderr = stderr_buffer[0]

        if check and retcode not in (0, 2):
            raise TerraformCommandError(retcode, argv, stdout, stderr)
        return retcode, stdout, stderr

    @staticmethod
    def _fdread(std_fd, std_buffer):
        with os.fdopen(std_fd, encoding="utf-8") as std_f:
            std = std_f.read()
            std_buffer.append(std)

    def stream(
        self,
        cmd: CmdType,
        args: Optional[Sequence[str]] = None,
        options: Optional[dict] = None,
        chdir=None,
        json: bool = True,
        check: bool = False,
    ) -> TerraformStream:
        """Run a command and stream its output as it is produced.

        Returns a `TerraformStream`. Iterating it yields parsed ``-json``
        events when ``json=True`` (the default) or raw text lines otherwise.

        :param cmd: Terraform command.
        :param args: Terraform command argument list.
        :param options: Terraform command options (same conversion as
            `run()`).
        :param chdir: Switch to a different working directory first.
        :param json: Whether to request ``-json`` output and parse each line.
        :param check: Whether to raise on a non ``0``/``2`` exit code at the end.
        """
        argv = _build_argv(cmd, args, options, chdir, json)
        return TerraformStream(argv, json=json, check=check)

    def plan_stream(
        self,
        json: bool = True,
        check: bool = False,
        vars: Optional[dict] = None,
        var_files: Optional[List[str]] = None,
        **options,
    ) -> TerraformStream:
        """Stream ``terraform plan`` output. See `stream()`.

        ``vars`` and ``var_files`` map to ``-var`` / ``-var-file`` like
        `plan()`. Other keyword options are converted to CLI flags, e.g.
        ``refresh=False`` or ``target="module.app"``.
        """
        _merge_var_options(options, vars, var_files)
        return self.stream(
            "plan", options=options, chdir=self.cwd, json=json, check=check
        )

    def apply_stream(
        self,
        json: bool = True,
        check: bool = False,
        auto_approve: bool = True,
        input: bool = False,
        vars: Optional[dict] = None,
        var_files: Optional[List[str]] = None,
        **options,
    ) -> TerraformStream:
        """Stream ``terraform apply`` output. See `stream()`.

        Defaults to ``auto_approve=True`` and ``input=False`` for unattended use.
        ``vars`` and ``var_files`` map to ``-var`` / ``-var-file`` like
        `apply()`. Other keyword options are converted to CLI flags.
        """
        options.update(auto_approve=auto_approve, input=input)
        _merge_var_options(options, vars, var_files)
        return self.stream(
            "apply", options=options, chdir=self.cwd, json=json, check=check
        )

    def version(
        self, check: bool = False, json: bool = True, **options
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/version

        Displays the version of Terraform and all installed plugins.

        By default, this assumes you want to get json output

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param options: More command options.
        """
        retcode, stdout, stderr = self.run(
            "version", options=options, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json)

    def init(
        self,
        check: bool = False,
        backend: bool = None,
        backend_config: Union[str, List[str]] = None,
        force_copy: bool = None,
        from_module: str = None,
        get: bool = None,
        input: bool = False,
        lock: bool = None,
        lock_timeout: str = None,
        no_color: bool = True,
        plugin_dirs: List[str] = None,
        reconfigure: bool = None,
        migrate_state: bool = None,
        upgrade: bool = None,
        lockfile: str = None,
        ignore_remote_version: bool = None,
        test_directory: str = None,
        enable_pluggable_state_storage_experiment: bool = None,
        create_default_workspace: bool = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/init

        Initialize a new or existing Terraform working directory by creating
        initial files, loading any remote state, downloading modules, etc.

        This is the first command that should be run for any new or existing
        Terraform configuration per machine. This sets up all the local data
        necessary to run Terraform that is typically not committed to version
        control.

        This command is always safe to run multiple times. Though subsequent runs
        may give errors, this command will never delete your configuration or
        state. Even so, if you have important information, please back it up prior
        to running this command, just in case.

        By default, this assumes you want to get json output.

        :param check: Whether to check return code.
        :param backend: False to disable backend or HCP Terraform initialization
            for this configuration and use what was previously initialized instead.
        :param backend_config: Configuration to be merged with what is in the
            configuration file's 'backend' block. This can be either a path to an
            HCL file with key/value assignments (same format as terraform.tfvars)
            or a 'key=value' format, and can be specified multiple times. The backend
            type must be in the configuration itself
        :param force_copy: Suppress prompts about copying state data when initializating
            a new state backend. This is equivalent to providing a "yes" to all
            confirmation prompts.
        :param from_module: Copy the contents of the given module into the target
            directory before initialization.
        :param get: False to disable downloading modules for this configuration.
        :param input: False to disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True to output not contain any color.
        :param plugin_dirs: Directories containing plugin binaries. This overrides all
            default search paths for plugins, and prevents the automatic installation
            of plugins.
        :param reconfigure: Reconfigure a backend, ignoring any saved configuration.
        :param migrate_state: Reconfigure a backend, and attempt to migrate any
            existing state.
        :param upgrade: Install the latest module and provider versions allowed within
            configured constraints, overriding the default behavior of selecting exactly
            the version recorded in the dependency lockfile.
        :param lockfile: Set a dependency lockfile mode.
            Currently only "readonly" is valid.
        :param ignore_remote_version: A rare option used for HCP Terraform and the
            remote backend only. Set this to ignore checking that the local and remote
            Terraform versions use compatible state representations, making an operation
            proceed even when there is a potential mismatch.
            See the documentation on configuring Terraform with
            HCP Terraform or Terraform Enterprise for more information.
        :param test_directory: Set the Terraform test directory, defaults to "tests".
        :param enable_pluggable_state_storage_experiment: Enable Terraform's
            experimental pluggable state storage initialization path.
        :param create_default_workspace: Control whether Terraform creates the
            default workspace when initializing a state store for the first time.
        :param options: More command options.
        """
        options.update(
            backend=backend,
            backend_config=backend_config,
            force_copy=flag(force_copy),
            from_module=from_module,
            get=get,
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            plugin_dir=plugin_dirs,
            reconfigure=flag(reconfigure),
            migrate_state=flag(migrate_state),
            upgrade=upgrade,
            lockfile=lockfile,
            ignore_remote_version=flag(ignore_remote_version),
            test_directory=test_directory,
            enable_pluggable_state_storage_experiment=flag(
                enable_pluggable_state_storage_experiment
            ),
            create_default_workspace=create_default_workspace,
        )
        retcode, stdout, stderr = self.run(
            "init", options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr)

    def validate(
        self,
        check: bool = False,
        json: bool = True,
        no_color: bool = True,
        no_test: bool = None,
        test_directory: str = None,
        query: bool = None,
        vars: dict = None,
        var_files: List[str] = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/validate

        Validate the configuration files in a directory, referring only to the
        configuration and not accessing any remote services such as remote state,
        provider APIs, etc.

        Validate runs checks that verify whether a configuration is syntactically
        valid and internally consistent, regardless of any provided variables or
        existing state. It is thus primarily useful for general verification of
        reusable modules, including correctness of attribute names and value types.

        It is safe to run this command automatically, for example as a post-save
        check in a text editor or as a test step for a re-usable module in a CI
        system.

        Validation requires an initialized working directory with any referenced
        plugins and modules installed. To initialize a working directory for
        validation without accessing any configured remote backend, use:
          self.init(backend=False)

        To verify configuration in the context of a particular run (a particular
        target workspace, input variable values, etc), use the self.plan()
        instead, which includes an implied validation check.

        By default, this assumes you want to get json output.

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param no_color: True to output not contain any color.
        :param no_test: If specified, Terraform will not validate test files.
        :param test_directory: Set the Terraform test directory, defaults to "tests".
        :param query: If specified, Terraform will also validate .tfquery.hcl files.
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            no_test=flag(no_test),
            test_directory=test_directory,
            query=flag(query),
            var=vars,
            var_file=var_files,
        )
        retcode, stdout, stderr = self.run(
            "validate", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def plan(
        self,
        check: bool = False,
        json: bool = True,
        destroy: bool = None,
        refresh_only: bool = None,
        refresh: bool = None,
        replace: Union[str, List[str]] = None,
        target: Union[str, List[str]] = None,
        vars: dict = None,
        var_files: List[str] = None,
        compact_warnings: bool = None,
        detailed_exitcode: bool = None,
        generate_config_out: str = None,
        input: bool = False,
        lock: bool = None,
        lock_timeout: str = None,
        no_color: bool = True,
        out: str = None,
        parallelism: int = None,
        state: str = None,
        **options,
    ) -> PlanResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/plan

        Generates a speculative execution plan, showing what actions Terraform
        would take to apply the current configuration. This command will not
        actually perform the planned actions.

        You can optionally save the plan to a file, which you can then pass to
        the self.apply() to perform exactly the actions described in the plan.

        By default, this assumes you want to get json output.

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param destroy: Select the "destroy" planning mode, which creates a plan
            to destroy all objects currently managed by this Terraform configuration
            instead of the usual behavior.
        :param refresh_only: Select the "refresh only" planning mode, which checks
            whether remote objects still match the outcome of the most recent Terraform
            apply but does not propose any actions to undo any changes made outside
            of Terraform.
        :param refresh: Skip checking for external changes to remote objects while
            creating the plan. This can potentially make planning faster, but at
            the expense of possibly planning against a stale record of the remote
            system state.
        :param replace: Force replacement of a particular resource instance using
            its resource address. If the plan would've normally produced an update or
            no-op action for this instance, Terraform will plan to replace it instead.
            You can use this option multiple times to replace more than one object.
        :param target: Limit the planning operation to only the given module, resource,
            or resource instance and all of its dependencies. You can use this option
            multiple times to include more than one object. This is for exceptional
            use only.
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param compact_warnings: If Terraform produces any warnings that are not
            accompanied by errors, shows them in a more compact form that includes
            only the summary messages.
        :param detailed_exitcode: Return detailed exit codes when the command exits.
            This will change the meaning of exit codes to:
            0 - Succeeded, diff is empty (no changes)
            1 - Errored
            2 - Succeeded, there is a diff
        :param generate_config_out: (Experimental) If import blocks are present in
            configuration, instructs Terraform to generate HCL
            for any imported resources not already present. The
            configuration is written to a new file at PATH,
            which must not already exist. Terraform may still
            attempt to write configuration if the plan errors.
        :param input: False to disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True to output not contain any color.
        :param out: Write a plan file to the given path. This can be used as
            input to the show or apply command.
        :param parallelism: Limit the number of concurrent operations. Defaults to 10.
        :param state: A legacy option used for the local backend only. See the
            local backend's documentation for more information.
        :param options: More command options.
        """
        options.update(
            destroy=flag(destroy),
            refresh_only=flag(refresh_only),
            refresh=refresh,
            replace=replace,
            target=target,
            var=vars,
            var_file=var_files,
            compact_warnings=flag(compact_warnings),
            detailed_exitcode=flag(detailed_exitcode),
            generate_config_out=generate_config_out,
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            out=out,
            parallelism=parallelism,
            state=state,
        )
        retcode, stdout, stderr = self.run(
            "plan", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout, split=True) if json else stdout
        return PlanResult(retcode, value, stderr, json=json)

    def query(
        self,
        check: bool = False,
        json: bool = True,
        vars: dict = None,
        var_files: List[str] = None,
        generate_config_out: str = None,
        no_color: bool = True,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/query

        Queries remote infrastructure for resources using .tfquery.hcl files.

        Terraform 1.13 registers this command only when experimental features
        are enabled.

        By default, this assumes you want to get json output.

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param vars: Set variables in the query file of the configuration.
        :param var_files: Load variable values from the given files, in addition
            to the default files terraform.tfvars and *.auto.tfvars.
        :param generate_config_out: Instructs Terraform to generate import and
            resource blocks for found results.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        options.update(
            var=vars,
            var_file=var_files,
            generate_config_out=generate_config_out,
            no_color=flag(no_color),
        )
        retcode, stdout, stderr = self.run(
            "query", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout, split=True) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def show(
        self,
        path: str = None,
        check: bool = False,
        json: bool = True,
        no_color: bool = True,
        vars: dict = None,
        var_files: List[str] = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/show

        Reads and outputs a Terraform state or plan file in a human-readable
        form. If no path is specified, the current state will be shown.

        By default, this assumes you want to get json output.

        :param path: Terraform state or plan file path.
        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param no_color: True to output not contain any color.
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            var=vars,
            var_file=var_files,
        )
        args = [path] if path else None
        retcode, stdout, stderr = self.run(
            "show", args, options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def apply(
        self,
        plan: str = None,
        check: bool = False,
        json: bool = True,
        auto_approve: bool = True,
        backup: str = None,
        compact_warnings: bool = None,
        input: bool = False,
        lock: bool = None,
        lock_timeout: str = None,
        no_color: bool = True,
        parallelism: int = None,
        state: str = None,
        state_out: str = None,
        destroy: bool = None,
        vars: dict = None,
        var_files: List[str] = None,
        **options,
    ) -> ApplyResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/apply

        Creates or updates infrastructure according to Terraform configuration
        files in the current directory.

        By default, Terraform will generate a new plan and present it for your
        approval before taking any action. You can optionally provide a plan
        file created by a previous call to self.plan(), in which case
        Terraform will take the actions described in that plan without any
        confirmation prompt.

        If you don't provide a saved plan file then this command will also accept
        all of the plan-customization options accepted by the terraform plan command.

        By default, this assumes you want to get json output.

        :param plan: Terraform plan file path.
        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param auto_approve: Skip interactive approval of plan before applying.
        :param backup: Path to backup the existing state file before modifying.
            Defaults to the `state_out` path with ".backup" extension.
            Set to "-" to disable backup.
        :param compact_warnings: If Terraform produces any warnings that are not
            accompanied by errors, shows them in a more compact form that includes
            only the summary messages.
        :param input: False to disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True to output not contain any color.
        :param parallelism: Limit the number of concurrent operations. Defaults to 10.
        :param state: Path to read and save state (unless `state_out` is specified).
            Defaults to "terraform.tfstate".
        :param state_out: Path to write state to that is different than `state`.
            This can be used to preserve the old state.
        :param destroy: Select the "destroy" planning mode, which creates a plan
            to destroy all objects currently managed by this Terraform configuration
            instead of the usual behavior.
        :param vars: Set variables in the root module of the configuration.
            With Terraform 1.10 and later, this can also provide apply-time
            ephemeral variables when applying a saved plan file.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param options: More command options.
        """
        options.update(
            auto_approve=flag(auto_approve),
            backup=backup,
            compact_warnings=flag(compact_warnings),
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            parallelism=parallelism,
            state=state,
            state_out=state_out,
            destroy=flag(destroy),
            var=vars,
            var_file=var_files,
        )
        args = [plan] if plan else None
        retcode, stdout, stderr = self.run(
            "apply", args, options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout, split=True) if json else stdout
        return ApplyResult(retcode, value, stderr, json=json)

    def destroy(
        self,
        check: bool = False,
        json: bool = True,
        auto_approve: bool = True,
        backup: str = None,
        compact_warnings: bool = None,
        input: bool = False,
        lock: bool = None,
        lock_timeout: str = None,
        no_color: bool = True,
        parallelism: int = None,
        state: str = None,
        state_out: str = None,
        **options,
    ) -> ApplyResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/destroy

        Destroy Terraform-managed infrastructure.

        By default, this assumes you want to get json output.

        This command is a convenience alias for:
            terraform apply -destroy

          This command also accepts many of the plan-customization options accepted by
          the terraform plan command. For more information on those options, run:
              terraform plan -help

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param auto_approve: Skip interactive approval of plan before applying.
        :param backup: Path to backup the existing state file before modifying.
            Defaults to the `state_out` path with ".backup" extension.
            Set to "-" to disable backup.
        :param compact_warnings: If Terraform produces any warnings that are not
            accompanied by errors, shows them in a more compact form that includes
            only the summary messages.
        :param input: False to disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True to output not contain any color.
        :param parallelism: Limit the number of concurrent operations. Defaults to 10.
        :param state: Path to read and save state (unless `state_out` is specified).
            Defaults to "terraform.tfstate".
        :param state_out: Path to write state to that is different than `state`.
            This can be used to preserve the old state.
        :param options: More command options.
        """
        options.update(
            auto_approve=flag(auto_approve),
            backup=backup,
            compact_warnings=flag(compact_warnings),
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            parallelism=parallelism,
            state=state,
            state_out=state_out,
        )
        retcode, stdout, stderr = self.run(
            "destroy", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout, split=True) if json else stdout
        return ApplyResult(retcode, value, stderr, json=json)

    def fmt(
        self,
        dir: Union[str, List[str]] = None,
        check: bool = False,
        no_color: bool = True,
        list: bool = None,
        write: bool = None,
        diff: bool = None,
        check_input: bool = None,
        recursive: bool = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/fmt

        Rewrites all Terraform configuration files to a canonical format. All
        configuration files (.tf), variables files (.tfvars), and testing files
        (.tftest.hcl) are updated. JSON files (.tf.json, .tfvars.json, or
        .tftest.json) are not modified.

        By default, fmt scans the current directory for configuration files. If you
        provide a directory for the target argument, then fmt will scan that
        directory instead. If you provide a file, then fmt will process just that
        file. If you provide a single dash ("-"), then fmt will read from standard
        input (STDIN).

        If DIR is not specified then the current working directory will be used.
        If DIR is "-" then content will be read from STDIN. The given content must
        be in the Terraform language native syntax; JSON is not supported.

        :param dir: Directory which Terraform configuration files located.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param list: False to not list files whose formatting differs
            (always disabled if using STDIN)
        :param write: False to not write to source files
            (always disabled if using STDIN or checkout_input=True)
        :param diff: Display diffs of formatting changes
        :param check_input: Check if the input is formatted.
            Exit status will be 0 if all input is properly formatted and non-zero otherwise.
        :param recursive: Also process files in subdirectories. By default, only the
            given directory (or current directory) is processed.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            list=list,
            write=write,
            diff=flag(diff),
            check=flag(check_input),
            recursive=flag(recursive),
        )
        if dir:
            args = dir
            if not isinstance(dir, List):
                args = [dir]
        else:
            args = None
        retcode, stdout, stderr = self.run(
            "fmt", args, options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr, json=False)

    def force_unlock(
        self,
        lock_id: str,
        check: bool = False,
        no_color: bool = True,
        force: bool = True,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/force-unlock

        Manually unlock the state for the defined configuration.

        This will not modify your infrastructure. This command removes the lock on the
        state for the current workspace. The behavior of this lock is dependent
        on the backend being used. Local state files cannot be unlocked by another
        process.

        :param lock_id: Lock ID.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param force: True to not ask for input for unlock confirmation.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            force=flag(force),
        )
        args = [lock_id]
        retcode, stdout, stderr = self.run(
            "force-unlock", args, options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr, json=False)

    def get(
        self,
        check: bool = False,
        no_color: bool = True,
        update: bool = None,
        test_directory: str = None,
        vars: dict = None,
        var_files: List[str] = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/get

        Downloads and installs modules needed for the configuration in the
        current working directory.

        This recursively downloads all modules needed, such as modules
        imported by modules imported by the root and so on. If a module is
        already downloaded, it will not be redownloaded or checked for updates
        unless the -update flag is specified.

        Module installation also happens automatically by default as part of
        the "terraform init" command, so you should rarely need to run this
        command separately.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param update: Check already-downloaded modules for available updates
            and install the newest versions available.
        :param test_directory: Set the Terraform test directory, defaults to "tests".
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            update=flag(update),
            test_directory=test_directory,
            var=vars,
            var_file=var_files,
        )
        retcode, stdout, stderr = self.run(
            "get", options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr, json=False)

    def graph(
        self,
        check: bool = False,
        no_color: bool = True,
        plan: str = None,
        draw_cycles: bool = None,
        type: str = None,
        module_depth: int = None,
        verbose: bool = None,
        vars: dict = None,
        var_files: List[str] = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/graph

        Produces a representation of the dependency graph between different
        objects in the current configuration and state.

        By default the graph shows a summary only of the relationships between
        resources in the configuration, since those are the main objects that
        have side-effects whose ordering is significant. You can generate more
        detailed graphs reflecting Terraform's actual evaluation strategy
        by specifying the -type=TYPE option to select an operation type.

        The graph is presented in the DOT language. The typical program that can
        read this format is GraphViz, but many web services are also available
        to read this format.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param plan: Render graph using the specified plan file instead of the
            configuration in the current directory.  Implies type=apply.
        :param draw_cycles: True to highlight any cycles in the graph with colored edges.
            This helps when diagnosing cycle errors. This option is
            supported only when illustrating a real evaluation graph,
            selected using the type=TYPE option.
        :param type: Type of operation graph to output. Can be: plan,
            plan-refresh-only, plan-destroy, or apply. By default
            Terraform just summarizes the relationships between the
            resources in your configuration, without any particular
            operation in mind. Full operation graphs are more detailed
            but therefore often harder to read.
        :param module_depth: Deprecated Terraform option that controls the
            depth of modules shown.
        :param verbose: Enable verbose graph output.
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            plan=plan,
            draw_cycles=flag(draw_cycles),
            type=type,
            module_depth=module_depth,
            verbose=flag(verbose),
            var=vars,
            var_file=var_files,
        )
        retcode, stdout, stderr = self.run(
            "graph", options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr, json=False)

    def import_resource(
        self,
        addr: str,
        id: str,
        check: bool = False,
        config: str = None,
        input: bool = False,
        lock: bool = None,
        lock_timeout: str = None,
        no_color: bool = True,
        vars: dict = None,
        var_files: List[str] = None,
        ignore_remote_version: bool = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/import

        Import existing infrastructure into your Terraform state.

        This will find and import the specified resource into your Terraform
        state, allowing existing infrastructure to come under Terraform
        management without having to be initially created by Terraform.

        The current implementation of Terraform import can only import resources
        into the state. It does not generate configuration. A future version of
        Terraform will also generate configuration.

        The ADDR specified is the address to import the resource to. Please
        see the documentation online for resource addresses. The ID is a
        resource-specific ID to identify that resource being imported. Please
        reference the documentation for the resource type you're importing to
        determine the ID syntax to use. It typically matches directly to the ID
        that the provider uses.

        This command will not modify your infrastructure, but it will make
        network requests to inspect parts of your infrastructure relevant to
        the resource being imported.

        :param addr: The address to import the resource to.
            Please see the documentation online for resource addresses.
        :param id: The id is a resource-specific ID to identify that resource being imported.
            Please reference the documentation for the resource type you're importing to
            determine the ID syntax to use. It typically matches directly to the ID
            that the provider uses.
        :param check: Whether to check return code.
        :param config: Path to a directory of Terraform configuration files
            to use to configure the provider. Defaults to pwd.
            If no config files are present, they must be provided
            via the input prompts or env vars.
        :param input: False to disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True to output not contain any color.
        :param vars: Set variables in the Terraform configuration.
            This is only useful with the "config" option.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param ignore_remote_version: A rare option used for the remote backend only.
            See the remote backend documentation for more information.
        :param options: More command options.
        """
        options.update(
            config=config,
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            var=vars,
            var_file=var_files,
            ignore_remote_version=flag(ignore_remote_version),
        )
        args = [addr, id]
        retcode, stdout, stderr = self.run(
            "import", args, options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr, json=False)

    def output(
        self,
        name: str = None,
        check: bool = False,
        json: bool = True,
        no_color: bool = True,
        state: str = None,
        raw: bool = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/output

        Reads an output variable from a Terraform state file and prints
        the value. With no additional arguments, output will display all
        the outputs for the root module. If name is not specified, all
        outputs are printed.

        :param name: Name of output variable.
        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param no_color: True to output not contain any color.
        :param state: Path to the state file to read. Defaults to "terraform.tfstate".
            Ignored when remote state is used.
        :param raw: For value types that can be automatically converted to a string,
            will print the raw string directly, rather than a human-oriented
            representation of the value.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            state=state,
            raw=flag(raw),
        )
        args = [name] if name else None
        retcode, stdout, stderr = self.run(
            "output", args, options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def modules(
        self,
        check: bool = False,
        json: bool = True,
        vars: dict = None,
        var_files: List[str] = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/modules

        Prints source and version data about all declared modules in Terraform
        configuration for the current working directory.

        By default, this assumes you want to get json output.

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param options: More command options.
        """
        options.update(
            var=vars,
            var_file=var_files,
        )
        retcode, stdout, stderr = self.run(
            "modules", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def providers(
        self,
        subcmd: str = None,
        args: Sequence[str] = None,
        check: bool = False,
        no_color: bool = True,
        json: bool = False,
        test_directory: str = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/providers

        Prints out a tree of modules in the referenced configuration annotated with
        their provider requirements.

        This provides an overview of all of the provider requirements across all
        referenced modules, as an aid to understanding why particular provider
        plugins are needed and why particular versions are selected.

        :param subcmd: Sub commands: lock, mirror and schema.
        :param args: Args for command.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param json: Whether to load stdout as json. Only valid when subcmd=schema.
        :param test_directory: Set the Terraform test directory, defaults to "tests".
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            test_directory=test_directory,
        )
        cmd = ["providers"]
        if subcmd:
            cmd.append(subcmd)
        retcode, stdout, stderr = self.run(
            cmd, args=args, options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def providers_lock(
        self,
        *providers,
        check: bool = False,
        no_color: bool = True,
        fs_mirror: str = None,
        net_mirror: str = None,
        platform: Union[str, List[str]] = None,
        enable_plugin_cache: bool = False,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/providers/lock

        Normally the dependency lock file (.terraform.lock.hcl) is updated
        automatically by "terraform init", but the information available to the
        normal provider installer can be constrained when you're installing providers
        from filesystem or network mirrors, and so the generated lock file can end
        up incomplete.

        The "providers lock" subcommand addresses that by updating the lock file
        based on the official packages available in the origin registry, ignoring
        the currently-configured installation strategy.

        After this command succeeds, the lock file will contain suitable checksums
        to allow installation of the providers needed by the current configuration
        on all of the selected platforms.

        By default, this command updates the lock file for every provider declared
        in the configuration. You can override that behavior by providing one or
        more provider source addresses on the command line.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param fs_mirror: Consult the given filesystem mirror directory instead of
            the origin registry for each of the given providers.
            This would be necessary to generate lock file entries for a provider
            that is available only via a mirror, and not published in an upstream registry.
            In this case, the set of valid checksums will be limited only to what Terraform
            can learn from the data in the mirror directory.
        :param net_mirror: Consult the given network mirror (given as a base URL)
            instead of the origin registry for each of the given providers.
            This would be necessary to generate lock file entries for a provider
            that is available only via a mirror, and not published in an upstream registry.
            In this case, the set of valid checksums will be limited only to what Terraform
            can learn from the data in the mirror indices.
        :param platform: Choose a target platform to request package checksums for.
            By default, Terraform will request package checksums suitable only for
            the platform where you run this command. Use this option multiple times
            to include checksums for multiple target systems.
            Target names consist of an operating system and a CPU architecture. For example,
            "linux_amd64" selects the Linux operating system running on an AMD64 or x86_64 CPU.
            Each provider is available only for a limited set of target platforms.
        :param enable_plugin_cache: Enable the usage of the globally configured plugin cache.
            This will speed up the locking process, but the providers
            wont be loaded from an authoritative source.
        :param options: More command options.
        """
        options.update(
            fs_mirror=fs_mirror,
            net_mirror=net_mirror,
            platform=platform,
            enable_plugin_cache=flag(enable_plugin_cache),
        )
        return self.providers(
            subcmd="lock", args=providers, check=check, no_color=no_color, **options
        )

    def providers_mirror(
        self,
        target_dir: str,
        check: bool = False,
        no_color: bool = True,
        platform: Union[str, List[str]] = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/providers/mirror

        Populates a local directory with copies of the provider plugins needed for
        the current configuration, so that the directory can be used either directly
        as a filesystem mirror or as the basis for a network mirror and thus obtain
        those providers without access to their origin registries in the future.

        The mirror directory will contain JSON index files that can be published
        along with the mirrored packages on a static HTTP file server to produce
        a network mirror. Those index files will be ignored if the directory is
        used instead as a local filesystem mirror.

        :param target_dir: Choose which target directory to build a mirror for.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param platform: Choose which target platform to build a mirror for.
            By default, Terraform will obtain plugin packages suitable for the
            platform where you run this command.
            Use this flag multiple times to include packages for multiple target systems.
            Target names consist of an operating system and a CPU architecture.
            For example, "linux_amd64" selects the Linux operating system running
            on an AMD64 or x86_64 CPU. Each provider is available only for a limited
            set of target platforms.
        :param options: More command options.
        """
        options.update(
            platform=platform,
        )
        args = [target_dir]
        return self.providers(
            subcmd="mirror", args=args, check=check, no_color=no_color, **options
        )

    def providers_schema(
        self,
        check: bool = False,
        no_color: bool = True,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/providers

        Prints out a json representation of the schemas for all providers used
        in the current configuration.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.providers(
            subcmd="schema", check=check, no_color=no_color, json=True, **options
        )

    def refresh(
        self,
        check: bool = False,
        json: bool = True,
        target: Union[str, List[str]] = None,
        vars: dict = None,
        var_files: List[str] = None,
        compact_warnings: bool = None,
        input: bool = False,
        lock: bool = None,
        lock_timeout: str = None,
        no_color: bool = True,
        parallelism: int = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/refresh

        Update the state file of your infrastructure with metadata that matches
        the physical resources they are tracking.

        This will not modify your infrastructure, but it can modify your
        state file to update metadata. This metadata might cause new changes
        to occur when you generate a plan or call apply next.

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param target: Resource to target. Operation will be limited to this resource and
            its dependencies. This flag can be used multiple times.
        :param vars: Set variables in the Terraform configuration.
        :param var_files: Load variable values from the given files, in addition to
            the default files terraform.tfvars and *.auto.tfvars.
        :param compact_warnings: If Terraform produces any warnings that are not
            accompanied by errors, shows them in a more compact form that includes
            only the summary messages.
        :param input: False to disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True to output not contain any color.
        :param parallelism: Limit the number of concurrent operations. Defaults to 10.
        :param options: More command options.
        """
        options.update(
            target=target,
            var=vars,
            var_file=var_files,
            compact_warnings=flag(compact_warnings),
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            parallelism=parallelism,
        )
        retcode, stdout, stderr = self.run(
            "refresh", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout, split=True) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def state(
        self,
        subcmd: str,
        args: Sequence[str] = None,
        check: bool = False,
        no_color: bool = True,
        json: bool = False,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state

        This command has subcommands for advanced state management.

        These subcommands can be used to slice and dice the Terraform state.
        This is sometimes necessary in advanced cases. For your safety, all
        state management commands that modify the state create a timestamped
        backup of the state prior to making modifications.

        The structure and output of the commands is specifically tailored to work
        well with the common Unix utilities such as grep, awk, etc. We recommend
        using those tools to perform more advanced state tasks.

        :param subcmd: Sub commands: identities, list, mv, pull, push,
            replace-provider, rm and show.
        :param args: Args for command.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param json: Whether to load stdout as json.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        cmd = ["state", subcmd]
        retcode, stdout, stderr = self.run(
            cmd, args=args, options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def state_list(
        self,
        *addrs,
        check: bool = False,
        no_color: bool = True,
        state: str = None,
        ids: Sequence[str] = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/list

        List resources in the Terraform state.

        An error will be returned if any of the resources or modules given as
        filter addresses do not exist in the state.

        :param addrs: Can be used to filter the instances by resource or module.
            If no pattern is given, all resource instances are listed.
            The addresses must either be module addresses or absolute resource
            addresses, such as:
                aws_instance.example
                module.example
                module.example.module.child
                module.example.aws_instance.example
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param state: Path to a Terraform state file to use to look up
            Terraform-managed resources. By default, Terraform will consult
            the state of the currently-selected workspace.
        :param ids: Filters the results to include only instances whose
            resource types have an attribute named "id" whose value is in
            the given ids.
        :param options: More command options.
        """
        options.update(id=ids)
        return self.state(
            "list", args=addrs, check=check, no_color=no_color, state=state, **options
        )

    def state_identities(
        self,
        *addrs,
        check: bool = False,
        no_color: bool = True,
        state: str = None,
        identity_id: str = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/v1.12.x/commands/state

        List the identities of resources in the Terraform state in JSON format.

        The address argument can be used to filter the instances by resource or
        module. If no pattern is given, identities for all resource instances are
        listed.

        :param addrs: Can be used to filter the instances by resource or module.
            If no pattern is given, all resource identities are listed.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param state: Path to a Terraform state file to use to look up
            Terraform-managed resources. By default, Terraform will consult
            the state of the currently-selected workspace.
        :param identity_id: Filters the results to include only instances whose
            resource types have an attribute named "id" whose value equals the
            given string.
        :param options: More command options.
        """
        options.update(state=state)
        if identity_id is not None:
            options.update(id=identity_id)
        return self.state(
            "identities",
            args=addrs,
            check=check,
            no_color=no_color,
            json=True,
            **options,
        )

    def state_mv(
        self,
        src: str,
        dst: str,
        check: bool = False,
        no_color: bool = True,
        dry_run: bool = None,
        lock: bool = None,
        lock_timeout: str = None,
        ignore_remote_version: bool = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/mv

        This command will move an item matched by the address given to the
        destination address. This command can also move to a destination address
        in a completely different state file.

        This can be used for simple resource renaming, moving items to and from
        a module, moving entire modules, and more. And because this command can also
        move data to a completely new state, it can also be used for refactoring
        one configuration into multiple separately managed Terraform configurations.

        This command will output a backup copy of the state prior to saving any
        changes. The backup cannot be disabled. Due to the destructive nature
        of this command, backups are required.

        If you're moving an item to a different state file, a backup will be created
        for each state file.

        :param src: Source address of resource.
        :param dst: Destination address of resource.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param dry_run: True to print out what would've been moved but doesn't
            actually move anything.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param ignore_remote_version: A rare option used for the remote backend only. See
            the remote backend documentation for more information.
        :param options: More command options.
        """
        options.update(
            dry_run=flag(dry_run),
            lock=lock,
            lock_timeout=lock_timeout,
            ignore_remote_version=flag(ignore_remote_version),
        )
        return self.state(
            "mv", args=[src, dst], check=check, no_color=no_color, **options
        )

    def state_pull(
        self,
        check: bool = False,
        no_color: bool = True,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/pull

        Pull the state from its location, upgrade the local copy, and output it.
        As part of this process, Terraform will upgrade the state format of the
        local copy to the current version.

        The primary use of this is for state stored remotely. This command
        will still work with local state but is less useful for this.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        cmd = ["state", "pull"]
        retcode, stdout, stderr = self.run(
            cmd, options=options, chdir=self.cwd, check=check
        )
        json = retcode == 0
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def state_push(
        self,
        path: str,
        check: bool = False,
        no_color: bool = True,
        force: bool = None,
        lock: bool = None,
        lock_timeout: str = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/push

        Update remote state from a local state file at path.
        The command will protect you against writing an older serial or a
        different state file lineage unless you specify the"force" flag.

        This command works with local state (it will overwrite the local
        state), but is less useful for this use case.

        If PATH is "-", then this command will read the state to push from stdin.
        Data from stdin is not streamed to the backend: it is loaded completely
        (until pipe close), verified, and then pushed.

        :param path: The path of the local state file.
        :param check: Whether to check return code.
        :param force: True to write the state even if lineages don't match or the
            remote serial is higher.
        :param no_color: True to output not contain any color.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param options: More command options.
        """
        options.update(
            force=flag(force),
            lock=lock,
            lock_timeout=lock_timeout,
        )
        return self.state(
            "push", args=[path], check=check, no_color=no_color, **options
        )

    def state_replace_provider(
        self,
        from_provider: str,
        to_provider: str,
        check: bool = False,
        no_color: bool = True,
        auto_approve: bool = True,
        lock: bool = None,
        lock_timeout: str = None,
        ignore_remote_version: bool = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/replace-provider

        Replace provider for resources in the Terraform state.

        :param from_provider: FROM_PROVIDER_FQN.
        :param to_provider: TO_PROVIDER_FQN.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param auto_approve: Skip interactive approval.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param ignore_remote_version: A rare option used for the remote backend only. See
            the remote backend documentation for more information.
        :param options: More command options.
        """
        options.update(
            lock=lock,
            lock_timeout=lock_timeout,
            auto_approve=flag(auto_approve),
            ignore_remote_version=flag(ignore_remote_version),
        )
        return self.state(
            "replace-provider",
            args=[from_provider, to_provider],
            check=check,
            no_color=no_color,
            **options,
        )

    def state_rm(
        self,
        *addrs,
        check: bool = False,
        no_color: bool = True,
        dry_run: bool = None,
        backup: str = None,
        lock: bool = None,
        lock_timeout: str = None,
        state: str = None,
        ignore_remote_version: bool = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/rm

        Remove one or more items from the Terraform state, causing Terraform to
        "forget" those items without first destroying them in the remote system.

        This command removes one or more resource instances from the Terraform state
        based on the addresses given. You can view and list the available instances
        with "terraform state list".

        If you give the address of an entire module then all of the instances in
        that module and any of its child modules will be removed from the state.

        If you give the address of a resource that has "count" or "for_each" set,
        all of the instances of that resource will be removed from the state.

        :param addrs: The address list of resources.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param dry_run: Path where Terraform should write the backup state.
        :param backup: True to print out what would've been moved but doesn't
            actually move anything.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param state: Path to the state file to update. Defaults to the current
            workspace state.
        :param ignore_remote_version: Continue even if remote and local Terraform
            versions are incompatible. This may result in an unusable workspace,
            and should be used with extreme caution.
        :param options: More command options.
        """
        options.update(
            dry_run=flag(dry_run),
            backup=backup,
            lock=lock,
            lock_timeout=lock_timeout,
            state=state,
            ignore_remote_version=flag(ignore_remote_version),
        )
        return self.state("rm", args=addrs, check=check, no_color=no_color, **options)

    def state_show(
        self,
        addr: str,
        check: bool = False,
        no_color: bool = True,
        state: str = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/state/show

        Shows the attributes of a resource in the Terraform state.

        This command shows the attributes of a single resource in the Terraform
        state. The address argument must be used to specify a single resource.
        You can view the list of available resources with "terraform state list".

        :param addr: The address of resource.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param state: Path to the state file to update. Defaults to the current
            workspace state.
        :param options: More command options.
        """
        options.update(
            state=state,
        )
        return self.state(
            "show", args=[addr], check=check, no_color=no_color, **options
        )

    def stacks(
        self,
        args: Sequence[str] = None,
        check: bool = False,
        no_color: bool = True,
        plugin_cache_dir: str = None,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/stacks

        Executes Terraform Stacks subcommands.

        The available subcommands depend on the Stacks plugin implementation.

        :param args: Args for the Stacks plugin command.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param plugin_cache_dir: Override the Stacks plugin cache directory.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            plugin_cache_dir=plugin_cache_dir,
        )
        retcode, stdout, stderr = self.run(
            "stacks", args=args, options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr)

    def taint(
        self,
        addr: str,
        check: bool = False,
        no_color: bool = True,
        allow_missing_config: bool = None,
        lock: bool = None,
        lock_timeout: str = None,
        ignore_remote_version: bool = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/taint

        Terraform uses the term "tainted" to describe a resource instance
        which may not be fully functional, either because its creation
        partially failed or because you've manually marked it as such using
        this command.

        This will not modify your infrastructure directly, but subsequent
        Terraform plans will include actions to destroy the remote object
        and create a new object to replace it.

        You can remove the "taint" state from a resource instance using
        the "terraform untaint" command.

        The address is in the usual resource address syntax, such as:
            aws_instance.foo
            aws_instance.bar[1]
            module.foo.module.bar.aws_instance.baz

        Use your shell's quoting or escaping syntax to ensure that the
        address will reach Terraform correctly, without any special
        interpretation.

        :param addr: The address of resource.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param allow_missing_config: True to regard the command will succeed (exit code 0)
            even if the resource is missing.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param ignore_remote_version: A rare option used for the remote backend only. See
            the remote backend documentation for more information.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            allow_missing_config=flag(allow_missing_config),
            lock=lock,
            lock_timeout=lock_timeout,
            ignore_remote_version=flag(ignore_remote_version),
        )
        retcode, stdout, stderr = self.run(
            "taint", args=[addr], options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr)

    def untaint(
        self,
        addr: str,
        check: bool = False,
        no_color: bool = True,
        allow_missing_config: bool = None,
        lock: bool = None,
        lock_timeout: str = None,
        ignore_remote_version: bool = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/untaint

        Terraform uses the term "tainted" to describe a resource instance
        which may not be fully functional, either because its creation
        partially failed or because you've manually marked it as such using
        the "terraform taint" command.

        This command removes that state from a resource instance, causing
        Terraform to see it as fully-functional and not in need of
        replacement.

        This will not modify your infrastructure directly. It only avoids
        Terraform planning to replace a tainted instance in a future operation.

        :param addr: The address of resource.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param allow_missing_config: True to regard the command will succeed (exit code 0)
            even if the resource is missing.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param ignore_remote_version: A rare option used for the remote backend only. See
            the remote backend documentation for more information.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            allow_missing_config=flag(allow_missing_config),
            lock=lock,
            lock_timeout=lock_timeout,
            ignore_remote_version=flag(ignore_remote_version),
        )
        retcode, stdout, stderr = self.run(
            "untaint", args=[addr], options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr)

    def test(
        self,
        check: bool = False,
        vars: dict = None,
        var_files: List[str] = None,
        no_color: bool = True,
        cloud_run: str = None,
        filter: Union[str, List[str]] = None,
        json: bool = True,
        junit_xml: str = None,
        test_directory: str = None,
        run_parallelism: int = None,
        verbose: bool = None,
        allow_deferral: bool = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/test

        Executes automated integration tests against the current Terraform
        configuration.

        Terraform will search for .tftest.hcl files within the current configuration
        and testing directories. Terraform will then execute the testing run blocks
        within any testing files in order, and verify conditional checks and
        assertions against the created infrastructure.

        This command creates real infrastructure and will attempt to clean up the
        testing infrastructure on completion. Monitor the output carefully to ensure
        this cleanup process is successful.

        By default, this assumes you want to get json output.

        :param check: Whether to check return code.
        :param vars: Set variables in the root module of the configuration.
        :param var_files: Load variable values from the given file, in addition
            to the default files terraform.tfvars and *.auto.tfvars.
        :param no_color: True to output not contain any color.
        :param cloud_run: If specified, Terraform will execute this test run
            remotely using HCP Terraform or Terraform Enterpise.
            You must specify the source of a module registered in
            a private module registry as the argument to this flag.
            This allows Terraform to associate the cloud run with
            the correct HCP Terraform or Terraform Enterprise module
            and organization.
        :param json: Whether to load stdout as json.
        :param junit_xml: Write a JUnit XML test report to the given file.
        :param test_directory: Set the Terraform test directory, defaults to "tests".
        :param run_parallelism: Limit the number of test runs that can execute
            in parallel within a file. Defaults to 10.
        :param verbose: Print the plan or state for each test run block as it
            executes.
        :param allow_deferral: Allow deferred actions during test operations.
            Terraform accepts this flag only in experimental builds.
        :param options: More command options.
        """
        options.update(
            var=vars,
            var_file=var_files,
            no_color=flag(no_color),
            cloud_run=cloud_run,
            filter=filter,
            junit_xml=junit_xml,
            test_directory=test_directory,
            run_parallelism=run_parallelism,
            verbose=flag(verbose),
            allow_deferral=flag(allow_deferral),
        )
        retcode, stdout, stderr = self.run(
            "test", options=options, chdir=self.cwd, check=check, json=json
        )
        value = json_loads(stdout, split=True) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def workspace(
        self,
        subcmd: str,
        args: Sequence[str] = None,
        check: bool = False,
        no_color: bool = True,
        **options,
    ) -> CommandResult:
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/workspace

        new, list, show, select and delete Terraform workspaces.

        :param subcmd: Sub commands: list, mv, pull, push, replace-provider, rm and show.
        :param args: Args for command.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        cmd = ["workspace", subcmd]
        retcode, stdout, stderr = self.run(
            cmd, args=args, options=options, chdir=self.cwd, check=check
        )
        return CommandResult(retcode, stdout, stderr)

    def workspace_new(
        self,
        name: str,
        check: bool = False,
        no_color: bool = True,
        lock: bool = None,
        lock_timeout: str = None,
        state: str = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/workspace/new

        Create a new Terraform workspace.

        :param name: Workspace name.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param state: Copy an existing state file into the new workspace.
        :param options: More command options.
        """
        options.update(
            lock=lock,
            lock_timeout=lock_timeout,
        )
        return self.workspace(
            "new", args=[name], check=check, no_color=no_color, state=state, **options
        )

    def workspace_list(
        self,
        check: bool = False,
        no_color: bool = True,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/workspace/list

        List Terraform workspaces.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.workspace("list", check=check, no_color=no_color, **options)

    def workspace_show(
        self,
        check: bool = False,
        no_color: bool = True,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/workspace/show

        Show the name of the current workspace.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.workspace("show", check=check, no_color=no_color, **options)

    def workspace_select(
        self,
        name: str,
        check: bool = False,
        no_color: bool = True,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/workspace/select

        Select a different Terraform workspace.

        :param name: Workspace name.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.workspace(
            "select", args=[name], check=check, no_color=no_color, **options
        )

    def workspace_delete(
        self,
        name: str,
        check: bool = False,
        no_color: bool = True,
        force: bool = None,
        lock: bool = None,
        lock_timeout: str = None,
        **options,
    ):
        """Refer to https://developer.hashicorp.com/terraform/cli/commands/workspace/delete

        Delete a Terraform workspace.

        :param name: Workspace name.
        :param check: Whether to check return code.
        :param no_color: True to remove even a non-empty workspace.
        :param force: True to output not contain any color.
        :param lock: False to not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param options: More command options.
        """
        options.update(
            force=flag(force),
            lock=lock,
            lock_timeout=lock_timeout,
        )
        return self.workspace(
            "delete", args=[name], check=check, no_color=no_color, **options
        )
