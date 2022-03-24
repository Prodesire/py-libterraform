import os
import platform
import shutil
import subprocess

lib_filename = 'libterraform.dll' if platform.system() == 'Windows' else 'libterraform.so'
header_filename = 'libterraform.h'
tf_filename = 'libterraform.go'
root = os.path.dirname(os.path.abspath(__file__))
terraform_dirname = os.path.join(root, 'terraform')
tf_path = os.path.join(root, tf_filename)
tf_package_name = 'github.com/hashicorp/terraform'


class BuildError(Exception):
    pass


def build(setup_kwargs):
    """
    This function is mandatory in order to build the extensions.
    """
    if not os.path.exists(os.path.join(terraform_dirname, '.git')):
        raise BuildError(f'The directory {terraform_dirname} not exists or init. '
                         f'Please execute `git submodule init && git submodule update` to init it.')

    target_tf_path = os.path.join(terraform_dirname, tf_filename)
    lib_path = os.path.join(terraform_dirname, lib_filename)
    header_path = os.path.join(terraform_dirname, header_filename)
    shutil.copyfile(tf_path, target_tf_path)
    try:
        print('      - Building libterraform')
        subprocess.check_call(
            ['go', 'build', '-buildmode=c-shared', f'-o={lib_filename}', tf_package_name],
            cwd=terraform_dirname
        )
        shutil.move(lib_path, os.path.join(root, 'libterraform', lib_filename))
    finally:
        for path in (target_tf_path, header_path, lib_path):
            if os.path.exists(path):
                os.remove(path)

    return setup_kwargs


if __name__ == '__main__':
    build({})
