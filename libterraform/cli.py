import os
from ctypes import *
from threading import Thread
from typing import List, Sequence

from libterraform import _lib_tf
from libterraform.common import json_loads, WINDOWS, CmdType
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
            cmd: CmdType,
            args: Sequence[str] = None,
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
        if isinstance(cmd, (list, tuple)):
            argv.extend(cmd)
        else:
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
                        argv += [f'-{option}={val}']
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
        stdout_thread = Thread(target=cls._fdread, args=(r_stdout_fd, stdout_buffer))
        stdout_thread.daemon = True
        stdout_thread.start()
        stderr_thread = Thread(target=cls._fdread, args=(r_stderr_fd, stderr_buffer))
        stderr_thread.daemon = True
        stderr_thread.start()

        if WINDOWS:
            import msvcrt
            w_stdout_handle = msvcrt.get_osfhandle(w_stdout_fd)
            w_stderr_handle = msvcrt.get_osfhandle(w_stderr_fd)
            retcode = _run_cli(argc, c_argv, w_stdout_handle, w_stderr_handle)
        else:
            retcode = _run_cli(argc, c_argv, w_stdout_fd, w_stderr_fd)

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
        with os.fdopen(std_fd, encoding='utf-8') as std_f:
            std = std_f.read()
            std_buffer.append(std)

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
        """Refer to https://www.terraform.io/docs/commands/output

        Reads an output variable from a Terraform state file and prints
        the value. With no additional arguments, output will display all
        the outputs for the root module. If name is not specified, all
        outputs are printed.

        :param name: Name of output variable.
        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param no_color: True to output not contain any color.
        :param state: Path to the state file to read. Defaults to "terraform.tfstate".
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
        retcode, stdout, stderr = self.run('output', args, options=options, chdir=self.cwd, check=check, json=json)
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def providers(
            self,
            subcmd: str = None,
            args: Sequence[str] = None,
            check: bool = False,
            no_color: bool = True,
            json: bool = False,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/providers

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
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        cmd = ['providers']
        if subcmd:
            cmd.append(subcmd)
        retcode, stdout, stderr = self.run(cmd, args=args, options=options, chdir=self.cwd, check=check, json=json)
        value = json_loads(stdout) if json else stdout
        return CommandResult(retcode, value, stderr, json=json)

    def providers_lock(
            self,
            *providers,
            check: bool = False,
            no_color: bool = True,
            fs_mirror: str = None,
            net_mirror: str = None,
            platform: str = None,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/providers/lock

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
        :param options: More command options.
        """
        options.update(
            fs_mirror=fs_mirror,
            net_mirror=net_mirror,
            platform=platform,
        )
        return self.providers(subcmd='lock', args=providers, check=check, no_color=no_color, **options)

    def providers_mirror(
            self,
            target_dir: str,
            check: bool = False,
            no_color: bool = True,
            platform: str = None,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/providers/mirror

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
        return self.providers(subcmd='mirror', args=args, check=check, no_color=no_color, **options)

    def providers_schema(
            self,
            check: bool = False,
            no_color: bool = True,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/providers

        Prints out a json representation of the schemas for all providers used
        in the current configuration.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.providers(subcmd='schema', check=check, no_color=no_color, json=True, **options)

    def refresh(
            self,
            check: bool = False,
            json: bool = True,
            target: str = None,
            vars: dict = None,
            var_files: List[str] = None,
            compact_warnings: bool = None,
            input: bool = False,
            lock: bool = None,
            lock_timeout: str = None,
            no_color: bool = True,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/refresh

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
        )
        retcode, stdout, stderr = self.run('refresh', options=options, chdir=self.cwd, check=check, json=json)
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
        """Refer to https://www.terraform.io/docs/commands/state

        This command has subcommands for advanced state management.

        These subcommands can be used to slice and dice the Terraform state.
        This is sometimes necessary in advanced cases. For your safety, all
        state management commands that modify the state create a timestamped
        backup of the state prior to making modifications.

        The structure and output of the commands is specifically tailored to work
        well with the common Unix utilities such as grep, awk, etc. We recommend
        using those tools to perform more advanced state tasks.

        :param subcmd: Sub commands: list, mv, pull, push, replace-provider, rm and show.
        :param args: Args for command.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param json: Whether to load stdout as json.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
        )
        cmd = ['state', subcmd]
        retcode, stdout, stderr = self.run(cmd, args=args, options=options, chdir=self.cwd, check=check, json=json)
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
        """Refer to https://www.terraform.io/docs/commands/state/list

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
        options.update(
            id=ids
        )
        return self.state('list', args=addrs, check=check, no_color=no_color, state=state, **options)

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
        """Refer to https://www.terraform.io/docs/commands/state/mv

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
        return self.state('mv', args=[src, dst], check=check, no_color=no_color, **options)

    def state_pull(
            self,
            check: bool = False,
            no_color: bool = True,
            **options,
    ):
        """Refer to https://www.terraform.io/docs/commands/state/pull

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
        cmd = ['state', 'pull']
        retcode, stdout, stderr = self.run(cmd, options=options, chdir=self.cwd, check=check)
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
        """Refer to https://www.terraform.io/docs/commands/state/push

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
        return self.state('push', args=[path], check=check, no_color=no_color, **options)

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
        """Refer to https://www.terraform.io/cli/commands/state/replace-provider

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
        return self.state('replace-provider', args=[from_provider, to_provider],
                          check=check, no_color=no_color, **options)

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
        """Refer to https://www.terraform.io/cli/commands/state/rm

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
        return self.state('rm', args=addrs, check=check, no_color=no_color, **options)

    def state_show(
            self,
            addr: str,
            check: bool = False,
            no_color: bool = True,
            state: str = None,
            **options,
    ):
        """Refer to https://www.terraform.io/cli/commands/state/show

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
        return self.state('show', args=[addr], check=check, no_color=no_color, **options)

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
        """Refer to https://www.terraform.io/cli/commands/taint

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
        retcode, stdout, stderr = self.run('taint', args=[addr], options=options, chdir=self.cwd, check=check)
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
        """Refer to https://www.terraform.io/cli/commands/untaint

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
        retcode, stdout, stderr = self.run('untaint', args=[addr], options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr)

    def test(
            self,
            check: bool = False,
            no_color: bool = True,
            compact_warnings: bool = None,
            junit_xml: str = None,
            **options,
    ):
        """Refer to https://www.terraform.io/cli/commands/test

        This is an experimental command to help with automated integration
        testing of shared modules. The usage and behavior of this command is
        likely to change in breaking ways in subsequent releases, as we
        are currently using this command primarily for research purposes.

        In its current experimental form, "test" will look under the current
        working directory for a subdirectory called "tests", and then within
        that directory search for one or more subdirectories that contain
        ".tf" or ".tf.json" files. For any that it finds, it will perform
        Terraform operations similar to the following sequence of commands
        in each of those directories:
          terraform validate
          terraform apply
          terraform destroy

        The test configurations should not declare any input variables and
        should at least contain a call to the module being tested, which
        will always be available at the path ../.. due to the expected
        filesystem layout.

        The tests are considered to be successful if all of the above steps
        succeed.

        Test configurations may optionally include uses of the special
        built-in test provider terraform.io/builtin/test, which allows
        writing explicit test assertions which must also all pass in order
        for the test run to be considered successful.

        This initial implementation is intended as a minimally-viable
        product to use for further research and experimentation, and in
        particular it currently lacks the following capabilities that we
        expect to consider in later iterations, based on feedback:
            - Testing of subsequent updates to existing infrastructure,
              where currently it only supports initial creation and
              then destruction.
            - Testing top-level modules that are intended to be used for
              "real" environments, which typically have hard-coded values
              that don't permit creating a separate "copy" for testing.
            - Some sort of support for unit test runs that don't interact
              with remote systems at all, e.g. for use in checking pull
              requests from untrusted contributors.

        In the meantime, we'd like to hear feedback from module authors
        who have tried writing some experimental tests for their modules
        about what sorts of tests you were able to write, what sorts of
        tests you weren't able to write, and any tests that you were
        able to write but that were difficult to model in some way.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param compact_warnings: Use a more compact representation for warnings, if
             this command produces only warnings and no errors.
        :param junit_xml: In addition to the usual output, also write test
            results to the given file path in JUnit XML format.
            This format is commonly supported by CI systems, and they typically
            expect to be given a filename to search for in the test workspace
            after the test run finishes.
        :param options: More command options.
        """
        options.update(
            no_color=flag(no_color),
            compact_warnings=flag(compact_warnings),
            junit_xml=junit_xml,
        )
        retcode, stdout, stderr = self.run('test', options=options, chdir=self.cwd, check=check)
        return CommandResult(retcode, stdout, stderr)

    def workspace(
            self,
            subcmd: str,
            args: Sequence[str] = None,
            check: bool = False,
            no_color: bool = True,
            **options,
    ) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/workspace

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
        cmd = ['workspace', subcmd]
        retcode, stdout, stderr = self.run(cmd, args=args, options=options, chdir=self.cwd, check=check)
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
        """Refer to https://www.terraform.io/docs/commands/workspace/new

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
        return self.workspace('new', args=[name], check=check, no_color=no_color, state=state, **options)

    def workspace_list(
            self,
            check: bool = False,
            no_color: bool = True,
            **options,
    ):
        """Refer to https://www.terraform.io/docs/commands/workspace/list

        List Terraform workspaces.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.workspace('list', check=check, no_color=no_color, **options)

    def workspace_show(
            self,
            check: bool = False,
            no_color: bool = True,
            **options,
    ):
        """Refer to https://www.terraform.io/docs/commands/workspace/show

        Show the name of the current workspace.

        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.workspace('show', check=check, no_color=no_color, **options)

    def workspace_select(
            self,
            name: str,
            check: bool = False,
            no_color: bool = True,
            **options,
    ):
        """Refer to https://www.terraform.io/docs/commands/workspace/select

        Select a different Terraform workspace.

        :param name: Workspace name.
        :param check: Whether to check return code.
        :param no_color: True to output not contain any color.
        :param options: More command options.
        """
        return self.workspace('select', args=[name], check=check, no_color=no_color, **options)

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
        """Refer to https://www.terraform.io/docs/commands/workspace/delete

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
        return self.workspace('delete', args=[name], check=check, no_color=no_color, **options)
