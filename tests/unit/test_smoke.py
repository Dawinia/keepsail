def test_package_importable():
    import keepsail

    assert keepsail.__version__ == "0.1.0"
