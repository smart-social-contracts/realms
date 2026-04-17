#!/usr/bin/env python3
"""
Add per-extension `sidebar_label` (multilingual) to every extension's manifest.json.

Background — Issue #168 (Layered Realm)
---------------------------------------
The realm sidebar used to derive its display labels from `extensions.<id>.sidebar`
keys baked into realm_frontend's locale JSON files. With the Layered Realm work,
extensions are loaded at runtime from file_registry, and realm_frontend can no
longer assume that the labels are bundled. Each extension must therefore ship
its own multilingual sidebar label inside its manifest.

Contract
--------
After running this script, every extension manifest.json will include a
`sidebar_label` object of the form:

    "sidebar_label": {
        "en": "Voting",
        "es": "Votación",
        "de": "Abstimmung",
        "fr": "Vote",
        "it": "Voto",
        "zh-CN": "投票"
    }

The realm_backend `get_sidebar_manifests()` query echoes this object straight
through, and realm_frontend's Sidebar.svelte picks the entry for the active
locale (with graceful fallbacks: <lang> → "en" → first key → manifest.name →
extension id). See `src/realm_frontend/src/routes/(sidebar)/Sidebar.svelte`.

Idempotency
-----------
- Manifests that already have `sidebar_label` are left untouched (use
  `--force` to overwrite).
- Manifests for extension ids not in `LABELS` are left untouched and a
  warning is printed.
- Output JSON preserves the insertion order of existing keys; the new
  `sidebar_label` is appended just after `description` (or at the end if
  `description` is missing) so the diff is local and easy to review.

Usage
-----
    python3 scripts/add_sidebar_labels.py
    python3 scripts/add_sidebar_labels.py --force
    python3 scripts/add_sidebar_labels.py --extensions-dir ../realms-extensions/extensions
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable

# --- Translation table ------------------------------------------------------
# Keep this in sync with the locales actually shipped by realm_frontend
# (src/realm_frontend/src/lib/i18n/locales/*.json).  Adding a new locale here
# is enough — realm_frontend will pick it up automatically because the lookup
# is dynamic on the active $locale.
LOCALES = ("en", "es", "de", "fr", "it", "zh-CN")

LABELS: Dict[str, Dict[str, str]] = {
    "admin_dashboard": {
        "en": "Admin Dashboard",
        "es": "Panel de Administración",
        "de": "Admin-Dashboard",
        "fr": "Tableau de Bord Admin",
        "it": "Pannello Amministratore",
        "zh-CN": "管理控制台",
    },
    "codex_viewer": {
        "en": "Codex Viewer",
        "es": "Visor de Códex",
        "de": "Codex-Viewer",
        "fr": "Visionneuse de Codex",
        "it": "Visualizzatore Codex",
        "zh-CN": "Codex 查看器",
    },
    "erd_explorer": {
        "en": "ERD Explorer",
        "es": "Explorador ERD",
        "de": "ERD-Explorer",
        "fr": "Explorateur ERD",
        "it": "Esploratore ERD",
        "zh-CN": "ERD 浏览器",
    },
    "hello_world": {
        "en": "Hello World",
        "es": "Hola Mundo",
        "de": "Hallo Welt",
        "fr": "Bonjour le Monde",
        "it": "Ciao Mondo",
        "zh-CN": "你好世界",
    },
    "justice_litigation": {
        "en": "Justice & Litigation",
        "es": "Justicia y Litigios",
        "de": "Justiz & Rechtsstreit",
        "fr": "Justice et Litiges",
        "it": "Giustizia e Contenziosi",
        "zh-CN": "司法与诉讼",
    },
    "land_registry": {
        "en": "Land Registry",
        "es": "Registro de Tierras",
        "de": "Grundbuch",
        "fr": "Cadastre",
        "it": "Catasto",
        "zh-CN": "土地登记",
    },
    "llm_chat": {
        "en": "AI Assistant",
        "es": "Asistente IA",
        "de": "KI-Assistent",
        "fr": "Assistant IA",
        "it": "Assistente AI",
        "zh-CN": "AI 助手",
    },
    "market_place": {
        "en": "Extensions Marketplace",
        "es": "Tienda de Extensiones",
        "de": "Erweiterungs-Marktplatz",
        "fr": "Marché des Extensions",
        "it": "Mercato delle Estensioni",
        "zh-CN": "扩展市场",
    },
    "member_dashboard": {
        "en": "My Dashboard",
        "es": "Mi Panel",
        "de": "Mein Dashboard",
        "fr": "Mon Tableau de Bord",
        "it": "Mio Pannello",
        "zh-CN": "我的控制台",
    },
    "metrics": {
        "en": "Metrics",
        "es": "Métricas",
        "de": "Metriken",
        "fr": "Métriques",
        "it": "Metriche",
        "zh-CN": "指标",
    },
    "notifications": {
        "en": "Notifications",
        "es": "Notificaciones",
        "de": "Benachrichtigungen",
        "fr": "Notifications",
        "it": "Notifiche",
        "zh-CN": "通知",
    },
    "passport_verification": {
        "en": "Passport Verification",
        "es": "Verificación de Pasaporte",
        "de": "Pass-Verifizierung",
        "fr": "Vérification du Passeport",
        "it": "Verifica Passaporto",
        "zh-CN": "护照验证",
    },
    "public_dashboard": {
        "en": "Public Dashboard",
        "es": "Panel Público",
        "de": "Öffentliches Dashboard",
        "fr": "Tableau de Bord Public",
        "it": "Pannello Pubblico",
        "zh-CN": "公共控制台",
    },
    "system_info": {
        "en": "System Info",
        "es": "Información del Sistema",
        "de": "Systeminformationen",
        "fr": "Infos Système",
        "it": "Info Sistema",
        "zh-CN": "系统信息",
    },
    "task_monitor": {
        "en": "Task Monitor",
        "es": "Monitor de Tareas",
        "de": "Aufgaben-Monitor",
        "fr": "Moniteur de Tâches",
        "it": "Monitor Attività",
        "zh-CN": "任务监视器",
    },
    "test_bench": {
        "en": "Test Bench",
        "es": "Banco de Pruebas",
        "de": "Testumgebung",
        "fr": "Banc de Test",
        "it": "Banco di Prova",
        "zh-CN": "测试台",
    },
    "vault": {
        "en": "Treasury Vault",
        "es": "Bóveda del Tesoro",
        "de": "Schatzkammer",
        "fr": "Coffre du Trésor",
        "it": "Caveau del Tesoro",
        "zh-CN": "金库",
    },
    "voting": {
        "en": "Voting",
        "es": "Votación",
        "de": "Abstimmung",
        "fr": "Vote",
        "it": "Voto",
        "zh-CN": "投票",
    },
    "welcome": {
        "en": "Welcome",
        "es": "Bienvenida",
        "de": "Willkommen",
        "fr": "Bienvenue",
        "it": "Benvenuto",
        "zh-CN": "欢迎",
    },
    "zone_selector": {
        "en": "Zone Selector",
        "es": "Selector de Zona",
        "de": "Zonenauswahl",
        "fr": "Sélecteur de Zone",
        "it": "Selettore di Zona",
        "zh-CN": "区域选择器",
    },
}


def _default_extensions_dir() -> Path:
    here = Path(__file__).resolve().parent
    # repo layout: <root>/realms/scripts/<this>  and  <root>/realms-extensions/extensions/
    return (here.parent.parent / "realms-extensions" / "extensions").resolve()


def _load_json_preserving_order(path: Path) -> "OrderedDict[str, object]":
    # `object_pairs_hook=OrderedDict` keeps insertion order so the diff stays
    # local — important for code review of these manifests.
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=OrderedDict)


def _dump_json_preserving_order(path: Path, data: "OrderedDict[str, object]") -> None:
    # Match the project's existing manifest indentation (2 spaces, trailing nl).
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _insert_sidebar_label(
    manifest: "OrderedDict[str, object]",
    label: Dict[str, str],
) -> "OrderedDict[str, object]":
    """Return a NEW OrderedDict with `sidebar_label` placed right after
    `description` (so manifests stay readable). Falls back to appending."""
    if "description" not in manifest:
        new = OrderedDict(manifest)
        new["sidebar_label"] = label
        return new

    out: "OrderedDict[str, object]" = OrderedDict()
    inserted = False
    for k, v in manifest.items():
        out[k] = v
        if not inserted and k == "description":
            out["sidebar_label"] = label
            inserted = True
    return out


def _process(
    manifest_path: Path,
    *,
    force: bool,
    dry_run: bool,
) -> str:
    manifest = _load_json_preserving_order(manifest_path)
    ext_id = (manifest.get("name") or manifest_path.parent.name) if isinstance(manifest, dict) else manifest_path.parent.name

    label = LABELS.get(str(ext_id))
    if not label:
        return f"skip   {ext_id:<22} (no label table entry — extend LABELS in this script)"

    if "sidebar_label" in manifest and not force:
        return f"keep   {ext_id:<22} (already has sidebar_label; use --force to overwrite)"

    new_manifest = _insert_sidebar_label(manifest, label)

    if dry_run:
        return f"would  {ext_id:<22} +{','.join(label.keys())}"

    _dump_json_preserving_order(manifest_path, new_manifest)
    return f"write  {ext_id:<22} +{','.join(label.keys())}"


def _iter_extension_manifests(extensions_dir: Path) -> Iterable[Path]:
    if not extensions_dir.is_dir():
        raise SystemExit(f"Extensions dir not found: {extensions_dir}")
    for entry in sorted(extensions_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue
        manifest = entry / "manifest.json"
        if manifest.exists():
            yield manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--extensions-dir", type=Path, default=_default_extensions_dir(),
                   help="Path to the extensions repo dir (default: ../../realms-extensions/extensions)")
    p.add_argument("--force", action="store_true",
                   help="Overwrite an existing sidebar_label block")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would change without writing files")
    p.add_argument("--only", nargs="*", default=None,
                   help="Limit to specific extension ids (default: all)")
    args = p.parse_args(argv)

    targets = list(_iter_extension_manifests(args.extensions_dir))
    if args.only:
        wanted = set(args.only)
        targets = [m for m in targets if m.parent.name in wanted]
        missing = wanted - {m.parent.name for m in targets}
        for name in sorted(missing):
            print(f"skip   {name:<22} (not found under {args.extensions_dir})")

    print(f"# {len(targets)} manifest(s) under {args.extensions_dir}")
    for manifest_path in targets:
        try:
            line = _process(manifest_path, force=args.force, dry_run=args.dry_run)
        except Exception as e:  # noqa: BLE001
            line = f"error  {manifest_path.parent.name:<22} ({e})"
        print(line)

    print("# done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
