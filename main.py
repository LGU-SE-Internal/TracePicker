#!/usr/bin/env -S uv run -s


from rcabench_platform.v2.cli.main import main
from src.tracepicker.register_samplers import register_tracepicker_samplers
register_tracepicker_samplers()

if __name__ == "__main__":
    main(enable_builtin_algorithms=False)
