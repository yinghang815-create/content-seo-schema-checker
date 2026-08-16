# Contributing

Thank you for helping improve Content SEO Schema Checker.

Before opening a pull request:

1. Open an issue for new rules or configuration changes.
2. Keep the core dependency-free unless a dependency adds clear value.
3. Give every finding a stable, documented rule ID.
4. Add tests for valid and invalid input.
5. Run:

   ```bash
   python -m pip install -e .
   python -m unittest discover -s tests -v
   python -m compileall -q src tests
   ```

Contributions are licensed under the Apache License 2.0.
