"""Test runner for executing skill tests in a sandboxed environment."""

import json
import os
import sys
from pathlib import Path


def main() -> int:
    """Main entry point for test runner."""
    # Get input data from environment or stdin
    input_file = os.environ.get("TEST_INPUT_FILE")
    skill_path = os.environ.get("SKILL_PATH")

    if input_file and Path(input_file).exists():
        input_data = json.loads(Path(input_file).read_text())
    else:
        # Try to read from stdin
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            input_data = {}

    # Output the input data as JSON (for now, just echo)
    # In a real implementation, this would load and execute the skill
    print(
        json.dumps(
            {
                "status": "success",
                "input_received": input_data,
                "skill_path": skill_path,
                "message": "Test runner executed successfully",
            }
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
