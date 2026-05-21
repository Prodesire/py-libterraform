import os
import platform
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data['pure_python'] = False
        build_data['infer_tag'] = True

        target_arch = os.environ.get('TARGET_ARCH', '')
        lib_filename = 'libterraform.dll' if platform.system() == 'Windows' else 'libterraform.so'
        header_filename = 'libterraform.h'
        tf_filename = 'libterraform.go'
        root = os.path.dirname(os.path.abspath(__file__))
        terraform_dirname = os.path.join(root, 'terraform')
        tf_path = os.path.join(root, tf_filename)
        tf_package_name = 'github.com/hashicorp/terraform'
        plugin_patch_filename = 'plugin_patch.go'
        plugin_dirname = os.path.join(root, 'go-plugin')
        plugin_patch_path = os.path.join(root, plugin_patch_filename)

        if not os.path.exists(os.path.join(terraform_dirname, '.git')):
            raise RuntimeError(
                f'The directory {terraform_dirname} not exists or init. '
                f'Please execute `git submodule init && git submodule update` to init it.'
            )
        if not os.path.exists(os.path.join(plugin_dirname, '.git')):
            raise RuntimeError(
                f'The directory {plugin_dirname} not exists or init. '
                f'Please execute `git submodule init && git submodule update` to init it.'
            )

        target_plugin_patch_path = os.path.join(plugin_dirname, plugin_patch_filename)
        target_tf_path = os.path.join(terraform_dirname, tf_filename)
        target_tf_mod_path = os.path.join(terraform_dirname, 'go.mod')
        lib_path = os.path.join(terraform_dirname, lib_filename)
        header_path = os.path.join(terraform_dirname, header_filename)

        # Patch go-plugin
        print('      - Patching go-plugin package')
        shutil.copyfile(plugin_patch_path, target_plugin_patch_path)
        with open(target_tf_mod_path) as f:
            mod_content = f.read()
        with open(target_tf_mod_path, 'w') as f:
            modified_mod_content = (
                f'{mod_content}\n'
                f'replace github.com/hashicorp/go-plugin v1.4.3 => ../go-plugin'
            )
            f.write(modified_mod_content)

        # Build libterraform
        shutil.copyfile(tf_path, target_tf_path)
        try:
            print('      - Building libterraform')
            env = os.environ.copy()
            env['CGO_ENABLED'] = '1'
            if target_arch:
                env['GOARCH'] = target_arch
                if platform.system() == 'Darwin' and target_arch == 'amd64':
                    env['CC'] = 'clang -arch x86_64'
            subprocess.check_call(
                [
                    'go', 'build', '-buildmode=c-shared', f'-o={lib_filename}',
                    '-ldflags', '-X github.com/hashicorp/terraform/version.dev=no',
                    tf_package_name,
                ],
                cwd=terraform_dirname,
                env=env,
            )
            shutil.move(lib_path, os.path.join(root, 'libterraform', lib_filename))
        finally:
            for path in (target_plugin_patch_path, target_tf_path, header_path, lib_path):
                if os.path.exists(path):
                    os.remove(path)
            with open(target_tf_mod_path, 'w') as f:
                f.write(mod_content)
