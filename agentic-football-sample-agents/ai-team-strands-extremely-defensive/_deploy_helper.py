"""
Deploy helper for Windows.
Handles two known bugs in bedrock-agentcore-starter-toolkit on Windows:
1. Backslash path separators in zip entries (patches toolkit once)
2. Missing OTEL Linux shim (patches deps cache and retries)

Usage: python _deploy_helper.py <staging_dir>
Exit codes: 0=success, 1=failed
"""
import sys
import os
import subprocess
import zipfile
import pathlib
import re
import shutil

# Force UTF-8 output on Windows (prevents emoji encoding errors)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def ensure_toolkit_patched():
    """Ensure toolkit uses forward slashes in zip paths and entrypoint (one-time patch)."""
    try:
        import bedrock_agentcore_starter_toolkit
        pkg_dir = pathlib.Path(bedrock_agentcore_starter_toolkit.__file__).parent
        patched = False

        # Patch 1: Forward slashes in zip entries (package.py)
        package_py = pkg_dir / "utils" / "runtime" / "package.py"
        if package_py.exists():
            content = package_py.read_text(encoding="utf-8")
            if 'replace("\\\\", "/")' not in content:
                content = content.replace(
                    'zipf.write(Path(root) / file, file_rel)',
                    'zipf.write(Path(root) / file, file_rel.replace("\\\\", "/"))'
                )
                content = content.replace(
                    'zipf.write(file_path, arcname)',
                    'zipf.write(file_path, str(arcname).replace("\\\\", "/"))'
                )
                package_py.write_text(content, encoding="utf-8")
                patched = True

        # Patch 2: Forward slashes in entrypoint path sent to API (launch.py)
        launch_py = pkg_dir / "operations" / "runtime" / "launch.py"
        if launch_py.exists():
            content = launch_py.read_text(encoding="utf-8")
            old = 'entrypoint_path = str(entrypoint_abs.relative_to(source_dir))'
            new = 'entrypoint_path = str(entrypoint_abs.relative_to(source_dir)).replace("\\\\", "/")'
            if old in content and new not in content:
                content = content.replace(old, new)
                launch_py.write_text(content, encoding="utf-8")
                patched = True

        if patched:
            print("  [fix] Patched toolkit for Windows path separators", flush=True)
    except Exception as e:
        print(f"  [warn] Could not patch toolkit: {e}", flush=True)


def inject_otel_shim(staging_dir):
    """Inject OTEL Linux shim into the cached dependencies.zip."""
    agentcore_dir = staging_dir / ".bedrock_agentcore"
    if not agentcore_dir.exists():
        return False
    for agent_dir in agentcore_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        deps_zip = agent_dir / "dependencies.zip"
        if not deps_zip.exists():
            continue
        with zipfile.ZipFile(str(deps_zip), 'a') as z:
            if 'bin/opentelemetry-instrument' not in z.namelist():
                info = zipfile.ZipInfo('bin/opentelemetry-instrument')
                info.external_attr = 0o755 << 16
                z.writestr(info, (
                    '#!/usr/bin/env python3\n'
                    'import sys\n'
                    'from opentelemetry.instrumentation.auto_instrumentation import run\n'
                    'sys.exit(run())\n'
                ))
                print("  [fix] Injected OTEL Linux shim", flush=True)
                return True
    return False


def deploy(staging_dir):
    """Run agentcore deploy with streaming output. Returns (success, output)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["AGENTCORE_SUPPRESS_RECOMMENDATION"] = "1"

    proc = subprocess.Popen(
        ["agentcore", "deploy", "--auto-update-on-conflict"],
        cwd=str(staging_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
    )

    output_lines = []
    spinner_re = re.compile(r'^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏\s]+$')

    for line in proc.stdout:
        line = line.rstrip('\n')
        output_lines.append(line)
        if line.strip() and not spinner_re.match(line):
            cleaned = re.sub(r'^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏\s]+', '', line).strip()
            if cleaned:
                print(f"  {cleaned}", flush=True)

    proc.wait()
    output = '\n'.join(output_lines)
    success = proc.returncode == 0 and "Launch failed" not in output
    return success, output


def main():
    if len(sys.argv) < 2:
        print("Usage: python _deploy_helper.py <staging_dir>")
        sys.exit(1)

    staging_dir = pathlib.Path(sys.argv[1]).resolve()
    if not staging_dir.exists():
        print(f"  ERROR: Staging dir not found: {staging_dir}")
        sys.exit(1)

    # One-time toolkit patch for Windows
    ensure_toolkit_patched()

    # First deploy attempt
    print("  Deploying...", flush=True)
    success, output = deploy(staging_dir)

    if success:
        sys.exit(0)

    # Handle OTEL error: patch and retry
    if "OpenTelemetry instrumentation" in output and "not found" in output:
        print("  [fix] Patching OTEL shim and retrying...", flush=True)
        inject_otel_shim(staging_dir)
        success, output = deploy(staging_dir)
        if success:
            sys.exit(0)

    # Handle entrypoint error: destroy and retry clean
    if "entrypoint could not be found" in output:
        print("  [fix] Entrypoint error - destroying agent and retrying clean...", flush=True)
        # Extract agent name from config
        yaml_file = staging_dir / ".bedrock_agentcore.yaml"
        if yaml_file.exists():
            content = yaml_file.read_text()
            match = re.search(r'default_agent:\s*(\S+)', content)
            if match:
                agent_name = match.group(1)
                subprocess.run(
                    ["agentcore", "destroy", "--agent", agent_name, "--force"],
                    cwd=str(staging_dir), capture_output=True, text=True,
                    env={**os.environ, "AGENTCORE_SUPPRESS_RECOMMENDATION": "1"}
                )
                print(f"  Destroyed {agent_name}, redeploying...", flush=True)
        # Clear local cache
        cache = staging_dir / ".bedrock_agentcore"
        if cache.exists():
            shutil.rmtree(str(cache))
        success, output = deploy(staging_dir)
        # May hit OTEL again on fresh deploy
        if not success and "OpenTelemetry instrumentation" in output:
            inject_otel_shim(staging_dir)
            success, output = deploy(staging_dir)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
