# Arduino Raspberry Pi Sensor Hub Cleanup Design

## Goal

Turn the existing coursework repository into a reproducible reference project
for an Arduino-to-Raspberry-Pi-to-Flask sensor pipeline, while clearly
documenting its educational scope and operational limitations.

## Scope

- Rename the GitHub repository from `IoT` to `arduino-rpi-sensor-hub`.
- Replace the placeholder README with English documentation covering the
  architecture, hardware roles, serial protocol, setup, configuration, API,
  local simulation, security limitations, and project structure.
- Remove generated Python bytecode, the committed runtime SQLite database, and
  obsolete duplicate Arduino source files.
- Add `.gitignore`, `.env.example`, MIT `LICENSE`, and explicit Python
  dependency files.
- Require credentials and the gateway API key through environment variables;
  do not retain working default secrets.
- Require dashboard authentication for history deletion.
- Add focused Flask tests for authentication, data ingestion, command
  validation, and protected history deletion.

## Boundaries

- Preserve the current Flask, SQLite, Raspberry Pi, and Arduino architecture.
- Do not redesign the dashboard or split the single-file Flask application.
- Do not claim production readiness. The server remains an educational
  deployment without TLS, durable command storage, user management, or a
  production WSGI configuration.
- Do not change the Arduino serial protocol.

## Verification

- Compile all Python source files.
- Install declared development dependencies in an isolated virtual
  environment.
- Run the Flask test suite.
- Verify the server rejects startup when required secrets are absent.
- Validate the documented simulator workflow locally.

## Publication

Commit the cleanup on `codex/project-cleanup`, push it, rename the repository,
and open a draft pull request against `main`.
