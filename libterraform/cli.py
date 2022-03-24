import os
from ctypes import *
from json import loads as json_loads
from typing import List

from libterraform import _lib_tf
from libterraform.exceptions import TerraformCommandError

_run_cli = _lib_tf.RunCli
_run_cli.argtypes = [c_int64, POINTER(c_char_p), c_int64, c_int64]


def flag(value):
    return ... if value else None


class CommandResult:
    __slots__ = ('retcode', 'value', 'error', 'json')

    def __init__(self, retcode, value, error=None, json=False):
        self.retcode = retcode
        self.value = json_loads(value) if json else value
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

    @staticmethod
    def run(cmd, args: List[str] = None, options: dict = None, chdir=None, check=False) -> (int, str, str):
        """
        Run command with args and return a tuple (retcode, stdout, stderr).

        The returned object will have attributes retcode, value, json.

        If check is True and the return code was non-zero, it raises a
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
        :return: Command result tuple (retcode, stdout, stderr).
        """
        argv = []
        if chdir:
            argv.append(f'-chdir={chdir}')
        argv.append(cmd)
        if args:
            argv.extend(args)
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
                if isinstance(value, bool):
                    value = 'true' if value else 'false'
                argv += [f'-{option}={value}']
        argc = len(argv)
        c_argv = (c_char_p * argc)()
        c_argv[:] = [arg.encode('utf-8') for arg in argv]
        r_stdout_fd, w_stdout_fd = os.pipe()
        r_stderr_fd, w_stderr_fd = os.pipe()
        retcode = _run_cli(argc, c_argv, w_stdout_fd, w_stderr_fd)

        with os.fdopen(r_stdout_fd) as stdout_f, os.fdopen(r_stderr_fd) as stderr_f:
            stdout = stdout_f.read()
            stderr = stderr_f.read()

        if check and retcode != 0:
            raise TerraformCommandError(retcode, argv, stdout, stderr)
        return retcode, stdout, stderr

    def version(self, check=False, json=True, **options) -> CommandResult:
        """Refer to https://www.terraform.io/docs/commands/version.html

        Displays the version of Terraform and all installed plugins.

        By default, this assumes you want to get json output

        :param check: Whether to check return code.
        :param json: Whether to load stdout as json.
        :param options: More command options.
        """
        options.update(
            json=flag(json),
        )
        retcode, stdout, stderr = self.run('version', options=options, check=check)
        return CommandResult(retcode, stdout, stderr, json)

    def init(
            self,
            check=False,
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
        """Refer to https://www.terraform.io/docs/commands/init.html

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
        :param backend: False for disable backend or Terraform Cloud initialization
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
        :param get: False for disable downloading modules for this configuration.
        :param input: False for disable interactive prompts. Note that some actions may
            require interactive prompts and will error if input is disabled.
        :param lock: False for not hold a state lock during backend migration.
            This is dangerous if others might concurrently run commands against the
            same workspace.
        :param lock_timeout: Duration to retry a state lock.
        :param no_color: True for output not contain any color.
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
