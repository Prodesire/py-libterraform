import os
import shutil
import subprocess

root = os.path.dirname(os.path.abspath(__file__))
terraform_dirname = os.path.join(root, 'terraform')
lib_filename = 'libterraform.so'
header_filename = 'libterraform.h'
tf_filename = 'libterraform.go'
tf_path = os.path.join(root, tf_filename)


class BuildError(Exception):
    pass


def build(setup_kwargs):
    '''
    This function is mandatory in order to build the extensions.
    '''
    if not os.path.exists(terraform_dirname):
        raise BuildError(f'The directory {terraform_dirname} not exists. '
                         f'Please execute `git submodule update` to get it.')

    target_tf_path = os.path.join(terraform_dirname, tf_filename)
    lib_path = os.path.join(terraform_dirname, lib_filename)
    header_path = os.path.join(terraform_dirname, header_filename)
    shutil.copyfile(tf_path, target_tf_path)
    try:
        print('      - Building libterraform')
        subprocess.check_call(
            ['go', 'build', '-buildmode=c-shared', f'-o={lib_filename}', tf_filename],
            # shell=True,
            cwd=terraform_dirname
        )
        shutil.move(lib_path, os.path.join(root, 'py_terraform', lib_filename))
    finally:
        for path in (target_tf_path, header_path, lib_path):
            if os.path.exists(path):
                os.remove(path)

    return setup_kwargs


if __name__ == '__main__':
    build({})
