from scripts import normalize_wheel_tags


def test_normalize_linux_wheel_tags_rewrites_linux_platform_tag(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "libterraform-0.15.3-cp314-cp314-linux_x86_64.whl"
    wheel.write_text("wheel", encoding="utf-8")

    renamed = normalize_wheel_tags.normalize_wheel_tags(dist)

    assert renamed == [
        (
            wheel,
            dist / "libterraform-0.15.3-cp314-cp314-manylinux_2_35_x86_64.whl",
        )
    ]
    assert not wheel.exists()
    assert (dist / "libterraform-0.15.3-cp314-cp314-manylinux_2_35_x86_64.whl").exists()


def test_normalize_linux_wheel_tags_leaves_non_linux_wheels_unchanged(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    macos_wheel = dist / "libterraform-0.15.3-cp314-cp314-macosx_14_0_arm64.whl"
    manylinux_wheel = dist / "libterraform-0.15.3-cp314-cp314-manylinux_2_35_x86_64.whl"
    macos_wheel.write_text("wheel", encoding="utf-8")
    manylinux_wheel.write_text("wheel", encoding="utf-8")

    assert normalize_wheel_tags.normalize_wheel_tags(dist) == []
    assert macos_wheel.exists()
    assert manylinux_wheel.exists()
