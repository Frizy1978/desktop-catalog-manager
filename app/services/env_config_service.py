from __future__ import annotations

from pathlib import Path


class EnvConfigService:
    def __init__(self, env_path: Path) -> None:
        self._env_path = env_path

    def load_values(self, defaults: dict[str, str]) -> dict[str, str]:
        values = defaults.copy()
        if not self._env_path.exists():
            return values

        for raw_line in self._env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw_value = line.split("=", 1)
            key = key.strip()
            value = raw_value.strip().strip('"').strip("'")
            if key in values:
                values[key] = value
        return values

    def save_values(self, new_values: dict[str, str]) -> None:
        lines: list[str] = []
        if self._env_path.exists():
            lines = self._env_path.read_text(encoding="utf-8").splitlines()

        line_index_by_key: dict[str, int] = {}
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            line_index_by_key[key] = index

        for key, value in new_values.items():
            assignment = f"{key}={value}"
            if key in line_index_by_key:
                lines[line_index_by_key[key]] = assignment
            else:
                lines.append(assignment)

        if not lines:
            lines = [f"{key}={value}" for key, value in new_values.items()]

        content = "\n".join(lines).rstrip() + "\n"
        self._env_path.write_text(content, encoding="utf-8")
