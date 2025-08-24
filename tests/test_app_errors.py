def test_ux_error_constants_import():
    from quality.errors import BAD_CSV, MISSING_DATA, PIPELINE_FAIL

    assert MISSING_DATA.code.startswith("E-")
    assert BAD_CSV.hint
    assert PIPELINE_FAIL.title
