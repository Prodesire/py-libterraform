class LibTerraformError(Exception):
    pass


class TerraformCommandError(LibTerraformError):
    """Raised when TerraformCommand.run() is called with check=True and the process
    returns a non-zero exit status.

    Attributes:
      retcode, cmd, stdout, stderr
    """
    def __init__(self, retcode, cmd, stdout=None, stderr=None):
        self.retcode = retcode
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return f'Command {self.cmd!r} returned non-zero exit status {self.retcode}.'


class TerraformFdReadError(LibTerraformError):
    """Raised when TerraformCommand.run() is called and cannot read stdout/stderr.
    """
    def __init__(self, fd):
        self.fd = fd

    def __str__(self):
        return f'Read from fd {self.fd} error.'
