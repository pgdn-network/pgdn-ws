"""
Command-line interface for pgdn-notify.
"""

import json
import sys
import argparse
from typing import Dict, Any

from .notify import notify


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="pgdn-notify: A lightweight notification system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pgdn-notify data.json
  echo '{"type":"slack","body":"Alert","meta":{"channel":"#alerts"}}' | pgdn-notify -
  pgdn-notify --help
        """
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input file containing notification data (use '-' for stdin)"
    )
    
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="pgdn-notify 0.1.0"
    )
    
    args = parser.parse_args()
    
    try:
        # Read input data
        if args.input == "-":
            if sys.stdin.isatty():
                parser.print_help()
                sys.exit(1)
            data = read_json_from_stdin()
        else:
            data = read_json_from_file(args.input)
        
        # Send notification
        result = notify(data)
        
        # Output result
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
        
        # Exit with error code if notification failed
        if not result.get("success", False):
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        error_result = {
            "success": False,
            "type": "unknown",
            "error": str(e)
        }
        if args.pretty:
            print(json.dumps(error_result, indent=2), file=sys.stderr)
        else:
            print(json.dumps(error_result), file=sys.stderr)
        sys.exit(1)


def read_json_from_stdin() -> Dict[str, Any]:
    """Read and parse JSON from stdin."""
    try:
        content = sys.stdin.read().strip()
        if not content:
            raise ValueError("No input provided")
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from stdin: {e}")


def read_json_from_file(filepath: str) -> Dict[str, Any]:
    """Read and parse JSON from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"File not found: {filepath}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {filepath}: {e}")
    except Exception as e:
        raise ValueError(f"Error reading file {filepath}: {e}")


if __name__ == "__main__":
    main() 