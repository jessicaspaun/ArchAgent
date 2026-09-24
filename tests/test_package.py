from importlib import import_module


def test_archagent_package_is_importable() -> None:
    package = import_module("archagent")

    assert package.__name__ == "archagent"
