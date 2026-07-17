#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class InstallError(RuntimeError):
    pass


def info(message: str) -> None:
    print(f"\033[1;34m==>\033[0m {message}")


def success(message: str) -> None:
    print(f"\033[1;32m==>\033[0m {message}")


def warn(message: str) -> None:
    print(f"\033[1;33mwarning:\033[0m {message}", file=sys.stderr)


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
    capture: bool = False,
    sensitive: bool = False,
) -> subprocess.CompletedProcess[str]:
    if not sensitive:
        info("$ " + shlex.join(args))
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and completed.returncode != 0:
        if capture:
            if completed.stdout:
                print(completed.stdout, file=sys.stderr)
            if completed.stderr:
                print(completed.stderr, file=sys.stderr)
        raise InstallError(f"Command failed ({completed.returncode}): {shlex.join(args)}")
    return completed


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def ask_bool(prompt: str, default: bool = True) -> bool:
    marker = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{marker}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "д", "да"}


def choose(prompt: str, options: list[str], default: str) -> str:
    option_text = "/".join(options)
    while True:
        value = ask(f"{prompt} ({option_text})", default)
        if value in options:
            return value
        warn(f"Expected one of: {', '.join(options)}")


def random_password(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


@dataclass
class RemoteConfig:
    ssh: str
    ssh_port: int = 22
    ssh_identity: str = ""
    workdir: str = "/srv/casinoshiz"
    python: str = "python3"


@dataclass
class GitConfig:
    infrastructure_repo: str
    infrastructure_branch: str = "main"
    application_repo: str = ""
    application_branch: str = "main"
    github_owner: str = ""
    github_repository: str = ""


@dataclass
class DeploymentConfig:
    ingress_profile: str = "traefik"
    environment: str = "production"
    run_ansible: bool = True
    bootstrap_flux: bool = True
    clone_application: bool = True
    build_application_images: bool = False
    wait_timeout_seconds: int = 1200


@dataclass
class DomainConfig:
    frontend: str = "app.local"
    api: str = "api.local"
    admin: str = "admin.local"
    telegram: str = "bot.local"
    grafana: str = "grafana.local"


@dataclass
class SopsConfig:
    age_key_file: str = "~/.config/sops/age/keys.txt"


@dataclass
class InstallerConfig:
    remote: RemoteConfig
    git: GitConfig
    deployment: DeploymentConfig
    domains: DomainConfig
    sops: SopsConfig
    images: dict[str, dict[str, str]] = field(default_factory=dict)


def dict_get(data: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def load_config(path: Path | None, ssh_override: str | None) -> InstallerConfig:
    raw: dict[str, Any] = {}
    if path:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)

    ssh = ssh_override or dict_get(raw, "remote.ssh", "")
    if not ssh:
        ssh = ask("SSH target", "root@127.0.0.1")

    ingress = dict_get(raw, "deployment.ingress_profile", "")
    if not ingress:
        ingress = choose("Ingress profile", ["traefik", "nginx"], "traefik")

    infra_repo = dict_get(
        raw,
        "git.infrastructure_repo",
        "https://github.com/cpp20120/CasinoShiz.Infrastructure.git",
    )
    app_repo = dict_get(
        raw,
        "git.application_repo",
        "https://github.com/cpp20120/CasinoShiz.git",
    )

    return InstallerConfig(
        remote=RemoteConfig(
            ssh=ssh,
            ssh_port=int(dict_get(raw, "remote.ssh_port", 22)),
            ssh_identity=dict_get(raw, "remote.ssh_identity", ""),
            workdir=dict_get(raw, "remote.workdir", "/srv/casinoshiz"),
            python=dict_get(raw, "remote.python", "python3"),
        ),
        git=GitConfig(
            infrastructure_repo=infra_repo,
            infrastructure_branch=dict_get(raw, "git.infrastructure_branch", "main"),
            application_repo=app_repo,
            application_branch=dict_get(raw, "git.application_branch", "main"),
            github_owner=dict_get(raw, "git.github_owner", "cpp20120"),
            github_repository=dict_get(
                raw,
                "git.github_repository",
                "CasinoShiz.Infrastructure",
            ),
        ),
        deployment=DeploymentConfig(
            ingress_profile=ingress,
            environment=dict_get(raw, "deployment.environment", "production"),
            run_ansible=bool(dict_get(raw, "deployment.run_ansible", True)),
            bootstrap_flux=bool(dict_get(raw, "deployment.bootstrap_flux", True)),
            clone_application=bool(dict_get(raw, "deployment.clone_application", True)),
            build_application_images=bool(
                dict_get(raw, "deployment.build_application_images", False)
            ),
            wait_timeout_seconds=int(
                dict_get(raw, "deployment.wait_timeout_seconds", 1200)
            ),
        ),
        domains=DomainConfig(
            frontend=dict_get(raw, "domains.frontend", "app.local"),
            api=dict_get(raw, "domains.api", "api.local"),
            admin=dict_get(raw, "domains.admin", "admin.local"),
            telegram=dict_get(raw, "domains.telegram", "bot.local"),
            grafana=dict_get(raw, "domains.grafana", "grafana.local"),
        ),
        sops=SopsConfig(
            age_key_file=dict_get(
                raw,
                "sops.age_key_file",
                "~/.config/sops/age/keys.txt",
            )
        ),
        images=dict_get(raw, "images", {}) or {},
    )


class Installer:
    def __init__(self, config: InstallerConfig, repo_root: Path, dry_run: bool) -> None:
        self.config = config
        self.repo_root = repo_root
        self.dry_run = dry_run
        self.kubeconfig = repo_root / ".deploy" / "kubeconfig"
        self.generated_dir = repo_root / ".deploy" / "generated"
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ssh_base(self) -> list[str]:
        args = [
            "ssh",
            "-p",
            str(self.config.remote.ssh_port),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
        ]
        if self.config.remote.ssh_identity:
            args.extend(["-i", os.path.expanduser(self.config.remote.ssh_identity)])
        args.append(self.config.remote.ssh)
        return args

    @property
    def scp_base(self) -> list[str]:
        args = [
            "scp",
            "-P",
            str(self.config.remote.ssh_port),
            "-o",
            "StrictHostKeyChecking=accept-new",
        ]
        if self.config.remote.ssh_identity:
            args.extend(["-i", os.path.expanduser(self.config.remote.ssh_identity)])
        return args

    def require_tools(self) -> None:
        required = ["ssh", "scp", "git", "ansible-playbook", "kubectl", "flux", "sops", "age-keygen"]
        missing = [tool for tool in required if not command_exists(tool)]
        if missing:
            raise InstallError("Missing local tools: " + ", ".join(missing))

    def ssh(self, command: str, *, capture: bool = False, sensitive: bool = False) -> subprocess.CompletedProcess[str]:
        if self.dry_run:
            info("[dry-run remote] " + command)
            return subprocess.CompletedProcess([], 0, "", "")
        return run(
            self.ssh_base + [command],
            capture=capture,
            sensitive=sensitive,
        )

    def copy_to_remote(self, local: Path, remote_path: str, *, recursive: bool = False) -> None:
        args = self.scp_base.copy()
        if recursive:
            args.append("-r")
        args.extend([str(local), f"{self.config.remote.ssh}:{remote_path}"])
        if self.dry_run:
            info("[dry-run] " + shlex.join(args))
            return
        run(args)

    def check_repo(self) -> None:
        required = [
            self.repo_root / "ansible" / "playbooks" / "site.yml",
            self.repo_root / "clusters" / "production",
            self.repo_root / "profiles" / self.config.deployment.ingress_profile,
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise InstallError("Repository is missing required files:\n" + "\n".join(missing))

    def confirm(self) -> None:
        print()
        print("Deployment summary")
        print("------------------")
        print(f"SSH:              {self.config.remote.ssh}")
        print(f"Ingress:          {self.config.deployment.ingress_profile}")
        print(f"Infrastructure:   {self.config.git.infrastructure_repo}")
        print(f"Application:      {self.config.git.application_repo or '(not configured)'}")
        print(f"Remote directory: {self.config.remote.workdir}")
        print(f"Run Ansible:      {self.config.deployment.run_ansible}")
        print(f"Bootstrap Flux:   {self.config.deployment.bootstrap_flux}")
        print()
        if not ask_bool("Continue", True):
            raise InstallError("Cancelled")

    def test_ssh(self) -> None:
        info("Testing SSH access")
        self.ssh("printf 'ssh-ok\\n' && uname -a && id")

    def render_ingress_profile(self) -> None:
        profile_path = self.repo_root / "clusters/production/ingress-profile/kustomization.yaml"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            textwrap.dedent(
                f"""\
                apiVersion: kustomize.config.k8s.io/v1beta1
                kind: Kustomization
                resources:
                  - ../../../profiles/{self.config.deployment.ingress_profile}
                """
            ),
            encoding="utf-8",
        )

        if self.config.deployment.ingress_profile == "nginx":
            self.render_nginx_config()

    def render_nginx_config(self) -> None:
        template_path = self.repo_root / "profiles/nginx/nginx.conf.template"
        target_path = self.generated_dir / "nginx.conf"
        template = template_path.read_text(encoding="utf-8")

        common = textwrap.indent(
            textwrap.dedent(
                """\
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Host $host;
                proxy_set_header X-Forwarded-Port $server_port;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection $connection_upgrade;
                add_header X-Content-Type-Options nosniff always;
                add_header X-Frame-Options SAMEORIGIN always;
                """
            ).strip(),
            "        ",
        )

        replacements = {
            "__FRONTEND_HOST__": self.config.domains.frontend,
            "__API_HOST__": self.config.domains.api,
            "__ADMIN_HOST__": self.config.domains.admin,
            "__TELEGRAM_HOST__": self.config.domains.telegram,
            "        __COMMON_PROXY_HEADERS__": common,
        }
        for old, new in replacements.items():
            template = template.replace(old, new)

        target_path.write_text(template, encoding="utf-8")

        configmap = self.repo_root / "profiles/nginx/configmap.yaml"
        indented = textwrap.indent(template.rstrip(), "    ")
        configmap.write_text(
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            "metadata:\n"
            "  name: nginx-edge-config\n"
            "  namespace: edge\n"
            "data:\n"
            "  nginx.conf: |\n"
            f"{indented}\n",
            encoding="utf-8",
        )

    def configure_ansible(self) -> Path:
        inventory = self.generated_dir / "inventory.yml"
        target = self.config.remote.ssh
        if "@" in target:
            user, host = target.split("@", 1)
        else:
            user, host = getpass.getuser(), target

        identity = os.path.expanduser(self.config.remote.ssh_identity)
        identity_line = f"      ansible_ssh_private_key_file: {json.dumps(identity)}\n" if identity else ""

        inventory.write_text(
            textwrap.dedent(
                f"""\
                all:
                  hosts:
                    production:
                      ansible_host: {host}
                      ansible_user: {user}
                      ansible_port: {self.config.remote.ssh_port}
                """
            ) + identity_line,
            encoding="utf-8",
        )

        group_vars = self.repo_root / "ansible/group_vars/all.yml"
        group_vars.parent.mkdir(parents=True, exist_ok=True)
        group_vars.write_text(
            textwrap.dedent(
                f"""\
                ingress_profile: {self.config.deployment.ingress_profile}
                k3s_config_path: /etc/rancher/k3s/config.yaml
                casinoshiz_root: {self.config.remote.workdir}
                """
            ),
            encoding="utf-8",
        )
        return inventory

    def run_ansible(self, inventory: Path) -> None:
        if not self.config.deployment.run_ansible:
            warn("Skipping Ansible bootstrap")
            return
        info("Running Ansible bootstrap")
        args = [
            "ansible-playbook",
            "-i",
            str(inventory),
            str(self.repo_root / "ansible/playbooks/site.yml"),
            "--extra-vars",
            f"ingress_profile={self.config.deployment.ingress_profile}",
        ]
        if self.dry_run:
            info("[dry-run] " + shlex.join(args))
            return
        run(args, cwd=self.repo_root)

    def prepare_remote_checkout(self) -> None:
        workdir = shlex.quote(self.config.remote.workdir)
        infra_repo = shlex.quote(self.config.git.infrastructure_repo)
        infra_branch = shlex.quote(self.config.git.infrastructure_branch)
        app_repo = shlex.quote(self.config.git.application_repo)
        app_branch = shlex.quote(self.config.git.application_branch)

        command = f"""
        set -euo pipefail
        sudo mkdir -p {workdir}
        sudo chown "$(id -u):$(id -g)" {workdir}

        if [ -d {workdir}/infrastructure/.git ]; then
          git -C {workdir}/infrastructure fetch --all --prune
          git -C {workdir}/infrastructure checkout {infra_branch}
          git -C {workdir}/infrastructure pull --ff-only
        else
          rm -rf {workdir}/infrastructure
          git clone --branch {infra_branch} {infra_repo} {workdir}/infrastructure
        fi
        """
        if self.config.deployment.clone_application and self.config.git.application_repo:
            command += f"""
            if [ -d {workdir}/application/.git ]; then
              git -C {workdir}/application fetch --all --prune
              git -C {workdir}/application checkout {app_branch}
              git -C {workdir}/application pull --ff-only
            else
              rm -rf {workdir}/application
              git clone --branch {app_branch} {app_repo} {workdir}/application
            fi
            """
        self.ssh(textwrap.dedent(command))

    def fetch_kubeconfig(self) -> None:
        info("Fetching kubeconfig")
        self.kubeconfig.parent.mkdir(parents=True, exist_ok=True)
        result = self.ssh("sudo cat /etc/rancher/k3s/k3s.yaml", capture=True)
        if self.dry_run:
            return
        content = result.stdout
        host = self.config.remote.ssh.split("@", 1)[-1]
        content = re.sub(r"https://127\\.0\\.0\\.1:6443", f"https://{host}:6443", content)
        self.kubeconfig.write_text(content, encoding="utf-8")
        self.kubeconfig.chmod(0o600)

    def kubectl_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["KUBECONFIG"] = str(self.kubeconfig)
        return env

    def install_sops_key(self) -> None:
        age_key = Path(os.path.expanduser(self.config.sops.age_key_file))
        if not age_key.exists():
            raise InstallError(f"Age key does not exist: {age_key}")
        info("Installing age identity into flux-system")
        if self.dry_run:
            return

        env = self.kubectl_env()
        run(["kubectl", "create", "namespace", "flux-system", "--dry-run=client", "-o", "yaml"], env=env, capture=True)
        namespace_yaml = run(
            ["kubectl", "create", "namespace", "flux-system", "--dry-run=client", "-o", "yaml"],
            env=env,
            capture=True,
        ).stdout
        run(["kubectl", "apply", "-f", "-"], env=env, input_text=namespace_yaml)

        secret_yaml = run(
            [
                "kubectl",
                "create",
                "secret",
                "generic",
                "sops-age",
                "-n",
                "flux-system",
                f"--from-file=age.agekey={age_key}",
                "--dry-run=client",
                "-o",
                "yaml",
            ],
            env=env,
            capture=True,
            sensitive=True,
        ).stdout
        run(["kubectl", "apply", "-f", "-"], env=env, input_text=secret_yaml, sensitive=True)

    def bootstrap_flux(self) -> None:
        if not self.config.deployment.bootstrap_flux:
            warn("Skipping Flux bootstrap")
            return

        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            token = getpass.getpass("GitHub token for Flux bootstrap: ").strip()
        if not token:
            raise InstallError("A GitHub token is required for Flux bootstrap")

        owner = self.config.git.github_owner
        repository = self.config.git.github_repository
        if not owner or not repository:
            raise InstallError("git.github_owner and git.github_repository are required")

        info("Bootstrapping Flux")
        env = self.kubectl_env()
        env["GITHUB_TOKEN"] = token
        args = [
            "flux",
            "bootstrap",
            "github",
            f"--owner={owner}",
            f"--repository={repository}",
            f"--branch={self.config.git.infrastructure_branch}",
            "--path=clusters/production",
            "--personal",
        ]
        if self.dry_run:
            info("[dry-run] " + shlex.join(args))
            return
        run(args, env=env, sensitive=True)

    def build_and_import_images(self) -> None:
        if not self.config.deployment.build_application_images:
            warn("Skipping remote application image build")
            return
        if not self.config.images:
            raise InstallError("Image build requested but [images] mapping is empty")

        workdir = shlex.quote(self.config.remote.workdir)
        self.ssh(
            f"""
            set -euo pipefail
            cd {workdir}/application
            docker compose build
            """
        )

        for name, mapping in self.config.images.items():
            source = mapping.get("source", "")
            target = mapping.get("target", "")
            if not source or not target:
                raise InstallError(f"Invalid image mapping for {name}")
            safe_source = shlex.quote(source)
            safe_target = shlex.quote(target)
            archive = shlex.quote(f"/tmp/casinoshiz-{name}.tar")
            info(f"Importing image {name}: {source} -> {target}")
            self.ssh(
                f"""
                set -euo pipefail
                docker image inspect {safe_source} >/dev/null
                docker tag {safe_source} {safe_target}
                docker save {safe_target} -o {archive}
                sudo k3s ctr images import {archive}
                rm -f {archive}
                """
            )

    def wait_for_cluster(self) -> None:
        if self.dry_run:
            return
        info("Waiting for Flux and workloads")
        env = self.kubectl_env()
        deadline = time.time() + self.config.deployment.wait_timeout_seconds
        while time.time() < deadline:
            result = run(
                ["kubectl", "get", "kustomizations", "-A", "-o", "json"],
                env=env,
                check=False,
                capture=True,
            )
            if result.returncode == 0:
                try:
                    payload = json.loads(result.stdout)
                    items = payload.get("items", [])
                    if items:
                        all_ready = True
                        for item in items:
                            conditions = item.get("status", {}).get("conditions", [])
                            ready = any(
                                condition.get("type") == "Ready"
                                and condition.get("status") == "True"
                                for condition in conditions
                            )
                            all_ready = all_ready and ready
                        if all_ready:
                            success("All Flux Kustomizations are Ready")
                            break
                except json.JSONDecodeError:
                    pass
            time.sleep(10)
        else:
            warn("Timed out waiting for all Flux Kustomizations")

        run(["kubectl", "get", "nodes", "-o", "wide"], env=env, check=False)
        run(["kubectl", "get", "pods", "-A"], env=env, check=False)
        run(["kubectl", "get", "pvc", "-A"], env=env, check=False)
        run(["flux", "get", "all", "-A"], env=env, check=False)

    def run(self) -> None:
        self.require_tools()
        self.check_repo()
        self.confirm()
        self.test_ssh()
        self.render_ingress_profile()
        inventory = self.configure_ansible()

        info("Validating rendered repository")
        if not self.dry_run:
            run(["go-task", "clean"], cwd=self.repo_root)
            run(["go-task", "validate"], cwd=self.repo_root)

        self.prepare_remote_checkout()
        self.run_ansible(inventory)
        self.fetch_kubeconfig()
        self.install_sops_key()
        self.build_and_import_images()
        self.bootstrap_flux()
        self.wait_for_cluster()

        success("Installer finished")
        print(f"Use: export KUBECONFIG={self.kubeconfig}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive CasinoShiz Kubernetes installer",
    )
    parser.add_argument(
        "ssh",
        nargs="?",
        help="SSH target, for example root@203.0.113.10",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="TOML configuration file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without changing the remote host",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Reserved for future unattended confirmation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    try:
        config = load_config(args.config, args.ssh)
        Installer(config, repo_root, args.dry_run).run()
        return 0
    except (InstallError, KeyboardInterrupt) as error:
        print(f"\033[1;31merror:\033[0m {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
