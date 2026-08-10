#!/usr/bin/env python3
"""Validate every example against its schema, and every schema against draft 2020-12."""
import json, sys, pathlib
from jsonschema import Draft202012Validator

root = pathlib.Path(__file__).parent
failures = 0
for schema_path in sorted(root.glob("*.schema.json")):
    name = schema_path.name.replace(".schema.json", "")
    schema = json.loads(schema_path.read_text())
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as e:
        print(f"SCHEMA INVALID  {name}: {e}"); failures += 1; continue
    example_path = root / "examples" / f"{name}.example.json"
    if not example_path.exists():
        print(f"NO EXAMPLE      {name}"); failures += 1; continue
    instance = json.loads(example_path.read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        for e in errors:
            print(f"EXAMPLE INVALID {name} at /{'/'.join(map(str, e.path))}: {e.message}")
        failures += 1
    else:
        print(f"OK              {name}")
sys.exit(1 if failures else 0)
