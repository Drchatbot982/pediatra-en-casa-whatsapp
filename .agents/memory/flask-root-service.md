---
name: Flask root service routing
description: How Python apps in this workspace become browser-visible through the shared preview router.
---

For a Python web app that must own the browser-visible root path, use a registered artifact service with `previewPath = "/"` and a service path of `"/"`. A standalone workflow can run and expose a port while the shared proxy still returns “Backend Not Configured”.

**Why:** The shared preview router is driven by artifact service path metadata, not only by arbitrary workflow port bindings.

**How to apply:** Keep the app entrypoint at the workspace root if desired, but make artifact-owned commands use a path relative to their service directory (for example, `../../main.py` when the service directory is `artifacts/<slug>`).