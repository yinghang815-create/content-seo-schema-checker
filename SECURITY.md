# Security Policy

Security fixes are provided for the latest released version.

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting feature in the repository Security tab. Include the
affected version, minimal reproduction, impact, and suggested mitigation.

The CLI reads local content files. Treat untrusted inputs as data, avoid running
the checker with unnecessary filesystem permissions, and review SARIF before
uploading it if source paths are sensitive. The tool does not execute document
scripts or fetch remote URLs.
