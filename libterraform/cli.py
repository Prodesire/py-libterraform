import os
from ctypes import *
from threading import Thread
from typing import List

from libterraform import _lib_tf
from libterraform.common import json_loads, WINDOWS
from libterraform.exceptions import TerraformCommandError, TerraformFdReadError

_run_cli = _lib_tf.RunCli
_run_cli.argtypes = [c_int64, POINTER(c_char_p), c_int64, c_int64]


def flag(value):
    return ... if value else None


class CommandResult:
    __slots__ = ('retcode', 'value', 'error', 'json')

    def __init__(self, retcode, value, error=None, json=False):
        self.retcode = retcode
        self.value = value
        self.error = error
        self.json = json

    def __repr__(self):
        return f'<CommandResult retcode={self.retcode!r} json={self.json!r}>'


class TerraformCommand:
    """Terraform command line.

    https://www.terraform.io/
    """

    def __init__(self, cwd=None):
        self.cwd = cwd

    @classmethod
    def run(
            cls,
            cmd: str,
            args: List[str] = None,
            options: dict = None,
            chdir=None,
            check: bool = False,
            json=False
    ) -> (int, str, str):
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
        argv = []
        if chdir:
            argv.append(f'-chdir={chdir}')
        argv.append(cmd)
        if json:
            options = options if options is not None else {}
            options.update(json=flag(json))
        if options is not None:
            for option, value in options.items():
                if value is None:
                    continue
                if '_' in option:
                    option = option.replace('_', '-')
                if value is ...:
                    argv += [f'-{option}']
                    continue
                if isinstance(value, list):
                    for val in value:
                        argv += [f'-{option} {val}']
                    continue
                if isinstance(value, dict):
                    for k, v in value.items():
                        argv += [f'-{option}={k}={v}']
                    continue
                if isinstance(value, bool):
                    value = 'true' if value else 'false'
                argv += [f'-{option}={value}']
        if args:
            argv.extend(args)
        argc = len(argv)
        c_argv = (c_char_p * argc)()
        c_argv[:] = [arg.encode('utf-8') for arg in argv]
        r_stdout_fd, w_stdout_fd = os.pipe()
        r_stderr_fd, w_stderr_fd = os.pipe()

        stdout_buffer = []
        stderr_buffer = []
        t = Thread(target=cls._fdread, args=(r_stdout_fd, r_stderr_fd, stdout_buffer, stderr_buffer))
        t.daemon = True
        t.start()

        if WINDOWS:
            import msvcrt
            w_stdout_handle = msvcrt.get_osfhandle(w_stdout_fd)
            w_stderr_handle = msvcrt.get_osfhandle(w_stderr_fd)
            retcode = _run_cli(argc, c_argv, w_stdout_handle, w_stderr_handle)
        else:
            retcode = _run_cli(argc, c_argv, w_stdout_fd, w_stderr_fd)

        t.join()
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
    def _fdread(stdout_fd, stderr_fd, stdout_buffer, stderr_buffer):
        with os.fdopen(stdout_fd) as stdout_f, os.fdopen(stderr_fd) as stderr_f:
            stdout = stdout_f.read()
            stderr = stderr_f.read()
            stdout_buffer.append(stdout)
            stderr_buffer.append(stderr)

    def version(self, check: bool = False, json: bool = True, **options) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/version

        Displays the version of Terraform and all installed plugins.

        By default, this assumes you want to get json output

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param options: More command options.
        """
        retcode, stdout, stderr = self.run('version', options=options, check=check, json=json)
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json)

    def init(
            self,
            check: bool = False,
            backend: bool = None,
            backend_config: str = None,
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
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/init

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
        :param backend: False to disable backend or Terraform Cloud initialization
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
        :param ignore_remote_version: A rare option used for Terraform Cloud and the
            remote backend only. Set this to ignore checking that the local and remote
            Terraform versions use compatible state representations, making an operation
            proceed even when there is a potential mismatch.
            See the documentation on configuring Terraform with Terraform Cloud for more
            information.
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
        )
        retcode, stdout, stderr = self.run('init', options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr)

    def validate(
            self,
            check: bool = False,
            json: bool = True,
            no_color: bool = True,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/validate

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
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        retcode, stdout, stderr = self.run('validate', options=options, chdir=self.cwd, check=check, json=json)
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def plan(
            self,
            check: bool = False,
            json: bool = True,
            destroy: bool = None,
            refresh_only: bool = None,
            refresh: bool = None,
            replace: str = None,
            target: str = None,
            vars: dict = None,
            var_files: List[str] = None,
            compact_warnings: bool = None,
            detailed_exitcode: bool = None,
            input: bool = False,
            lock: bool = None,
            lock_timeout: str = None,
            no_color: bool = True,
            out: str = None,
            parallelism: int = None,
            state: str = None,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/plan

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
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            out=out,
            parallelism=parallelism,
            state=state,
        )
        retcode, stdout, stderr = self.run('plan', options=options, chdir=self.cwd, check=check, json=json)
        value = json_loads(stdout, split=True) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def show(
            self,
            path: str = None,
            check: bool = False,
            json: bool = True,
            no_color: bool = True,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/show

        Reads and outputs a Terraform state or plan file in a human-readable
        form. If no path is specified, the current state will be shown.

        By default, this assumes you want to get json output.

        :param path: Terraform state or plan file path.
        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        args = [path] if path else None
        retcode, stdout, stderr = self.run('show', args, options=options, chdir=self.cwd, check=check, json=json)
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
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/apply

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
        )
        args = [plan] if plan else None
        retcode, stdout, stderr = self.run('apply', args, options=options, chdir=self.cwd, check=check, json=json)
        value = json_loads(stdout, split=True) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

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
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/destroy

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
        retcode, stdout, stderr = self.run('destroy', options=options, chdir=self.cwd, check=check, json=json)
        value = json_loads(stdout, split=True) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def fmt(
            self,
            dir: str = None,
            check: bool = False,
            no_color: bool = True,
            list: bool = None,
            write: bool = None,
            diff: bool = None,
            check_input: bool = None,
            recursive: bool = None,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/fmt

        Rewrites all Terraform configuration files to a canonical format. Both
        configuration files (.tf) and variables files (.tfvars) are updated.
        JSON files (.tf.json or .tfvars.json) are not modified.

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
        args = [dir] if dir else None
        retcode, stdout, stderr = self.run('fmt', args, options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr, json=False)

    def force_unlock(
            self,
            lock_id: str,
            check: bool = False,
            no_color: bool = True,
            force: bool = True,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/force-unlock

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
        retcode, stdout, stderr = self.run('force-unlock', args, options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr, json=False)

    def graph(
            self,
            check: bool = False,
            no_color: bool = True,
            plan: str = None,
            draw_cycles: bool = None,
            type: str = None,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/graph

        Produces a representation of the dependency graph between different
        objects in the current configuration and state.

        The graph is presented in the DOT language. The typical program that can
        read this format is GraphViz, but many web services are also available
        to read this format.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param plan: Render graph using the specified plan file instead of the
            configuration in the current directory.
        :param draw_cycles: True to highlight any cycles in the graph with colored edges.
            This helps when diagnosing cycle errors.
        :param type: Type of graph to output. Can be: plan, plan-refresh-only, plan-destroy, or apply.
            By default, Terraform chooses "plan", or "apply" if you also set the plan=xxx option.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            plan=plan,
            draw_cycles=flag(draw_cycles),
            type=type,
        )
        retcode, stdout, stderr = self.run('graph', options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr, json=False)

    def import_resource(
            self,
            addr: str,
            id: str,
            check: bool = False,
            config: str = None,
            allow_missing_config: bool = None,
            input: bool = False,
            lock: bool = None,
            lock_timeout: str = None,
            no_color: bool = True,
            vars: dict = None,
            var_files: List[str] = None,
            ignore_remote_version: bool = None,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/import

        Import existing infrastructure into your Terraform state.

        This will find and import the specified resource into your Terraform
        state, allowing existing infrastructure to come under Terraform
        management without having to be initially created by Terraform.

        The current implementation of Terraform import can only import resources
        into the state. It does not generate configuration. A future version of
        Terraform will also generate configuration.

        Because of this, prior to running terraform import it is necessary to write
        a resource configuration block for the resource manually, to which the
        imported object will be attached.

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
        :param allow_missing_config: True to allow import when no resource configuration block exists.
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
            allow_missing_config=flag(allow_missing_config),
            input=input,
            lock=lock,
            lock_timeout=lock_timeout,
            no_color=flag(no_color),
            var=vars,
            var_file=var_files,
            ignore_remote_version=flag(ignore_remote_version),
        )
        args = [addr, id]
        retcode, stdout, stderr = self.run('import', args, options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr, json=False)
