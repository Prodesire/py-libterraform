import os
import platform
import re
import shutil
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def repository_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def submodule_paths(root):
    return (
        os.path.join(root, "upstream", "terraform"),
        os.path.join(root, "upstream", "go-plugin"),
    )


def native_go_source_paths(root):
    return (
        os.path.join(root, "native", "go", "libterraform.go"),
        os.path.join(root, "native", "go", "plugin_patch.go"),
    )


def go_plugin_version_from_mod(mod_content):
    match = re.search(
        r"^\s*github\.com/hashicorp/go-plugin\s+(v\S+)",
        mod_content,
        re.MULTILINE,
    )
    if match is None:
        raise RuntimeError(
            "Cannot find github.com/hashicorp/go-plugin in upstream/terraform/go.mod"
        )
    return match.group(1)


def go_mod_content_with_go_plugin_replace(mod_content, plugin_dir):
    clean_content = re.sub(
        r"\n*replace github\.com/hashicorp/go-plugin\s+v\S+\s+=>\s+\S+\s*$",
        "",
        mod_content,
        flags=re.MULTILINE,
    ).rstrip()
    plugin_version = go_plugin_version_from_mod(clean_content)
    patched_content = (
        f"{clean_content}\n\n"
        f"replace github.com/hashicorp/go-plugin {plugin_version} => {plugin_dir}\n"
    )
    return f"{clean_content}\n", patched_content


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        build_data["infer_tag"] = True

        target_arch = os.environ.get("TARGET_ARCH", "")
        lib_filename = (
            "libterraform.dll" if platform.system() == "Windows" else "libterraform.so"
        )
        header_filename = "libterraform.h"
        root = repository_root()
        terraform_dirname, plugin_dirname = submodule_paths(root)
        tf_path, plugin_patch_path = native_go_source_paths(root)
        tf_filename = os.path.basename(tf_path)
        tf_package_name = "github.com/hashicorp/terraform"
        plugin_patch_filename = os.path.basename(plugin_patch_path)

        if not os.path.exists(os.path.join(terraform_dirname, ".git")):
            raise RuntimeError(
                f"The directory {terraform_dirname} not exists or init. "
                f"Please execute `git submodule init && git submodule update` to init it."
            )
        if not os.path.exists(os.path.join(plugin_dirname, ".git")):
            raise RuntimeError(
                f"The directory {plugin_dirname} not exists or init. "
                f"Please execute `git submodule init && git submodule update` to init it."
            )

        target_plugin_patch_path = os.path.join(plugin_dirname, plugin_patch_filename)
        target_tf_path = os.path.join(terraform_dirname, tf_filename)
        target_tf_mod_path = os.path.join(terraform_dirname, "go.mod")
        lib_path = os.path.join(terraform_dirname, lib_filename)
        header_path = os.path.join(terraform_dirname, header_filename)

        # Patch go-plugin
        print("      - Patching go-plugin package")
        shutil.copyfile(plugin_patch_path, target_plugin_patch_path)
        with open(target_tf_mod_path) as f:
            mod_content, modified_mod_content = go_mod_content_with_go_plugin_replace(
                f.read(),
                "../go-plugin",
            )
        with open(target_tf_mod_path, "w") as f:
            f.write(modified_mod_content)

        # Build libterraform
        shutil.copyfile(tf_path, target_tf_path)
        try:
            print("      - Building libterraform")
            env = os.environ.copy()
            env["CGO_ENABLED"] = "1"
            if target_arch:
                env["GOARCH"] = target_arch
                if platform.system() == "Darwin" and target_arch == "amd64":
                    env["CC"] = "clang -arch x86_64"
            subprocess.check_call(
                [
                    "go",
                    "build",
                    "-buildmode=c-shared",
                    f"-o={lib_filename}",
                    "-ldflags",
                    "-X github.com/hashicorp/terraform/version.dev=no",
                    tf_package_name,
                ],
                cwd=terraform_dirname,
                env=env,
            )
            shutil.move(
                lib_path,
                os.path.join(root, "src", "libterraform", lib_filename),
            )
        finally:
            for path in (
                target_plugin_patch_path,
                target_tf_path,
                header_path,
                lib_path,
            ):
                if os.path.exists(path):
                    os.remove(path)
            with open(target_tf_mod_path, "w") as f:
                f.write(mod_content)
