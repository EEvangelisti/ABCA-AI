from source.tools.analysis_python import _run_analysis_script_impl


def main():
    result = _run_analysis_script_impl(
        "_sandbox_smoke_test.py"
    )

    print(result)


if __name__ == "__main__":
    main()
