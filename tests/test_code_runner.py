from executor.code_runner import CodeRunner, CodeSafetyError


def test_code_runner_executes_python_and_captures_output():
    runner = CodeRunner(timeout_seconds=2)
    result = runner.run("print('hello-black')").as_dict()

    assert result["success"] is True
    assert "hello-black" in result["stdout"]
    assert result["return_code"] == 0


def test_code_runner_blocks_forbidden_calls():
    runner = CodeRunner(timeout_seconds=2)

    try:
        runner.run("import os\nos.system('echo blocked')")
    except CodeSafetyError as error:
        assert "Forbidden" in str(error)
    else:
        raise AssertionError("CodeSafetyError was not raised")
