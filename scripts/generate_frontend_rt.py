#!/usr/bin/env python3
"""Generate frontend-rt/ boilerplate for all extensions that have a frontend/.

Creates package.json, vite.config.ts, tsconfig.json, .gitignore, and
src/index.ts for each extension. The Svelte components must be created
separately — this script only generates the scaffolding.
"""

import json
import os
import sys

EXTENSIONS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "extensions", "extensions",
)

SKIP = {"_shared", "package_manager"}

def pascal_case(name: str) -> str:
    return "".join(w.capitalize() for w in name.split("_"))

def generate(ext_name: str, ext_dir: str):
    rt_dir = os.path.join(ext_dir, "frontend-rt")
    src_dir = os.path.join(rt_dir, "src")
    os.makedirs(src_dir, exist_ok=True)

    component = pascal_case(ext_name)

    with open(os.path.join(rt_dir, "package.json"), "w") as f:
        json.dump({
            "name": f"{ext_name}-frontend-rt",
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {"build": "vite build"},
            "devDependencies": {
                "@sveltejs/vite-plugin-svelte": "^5.0.0",
                "svelte": "^5.19.0",
                "typescript": "^5.4.0",
                "vite": "^6.0.0",
            },
        }, f, indent=2)
        f.write("\n")

    with open(os.path.join(rt_dir, "vite.config.ts"), "w") as f:
        f.write(f"""import {{ defineConfig }} from 'vite';
import {{ svelte }} from '@sveltejs/vite-plugin-svelte';
import {{ resolve }} from 'node:path';

export default defineConfig({{
\tplugins: [svelte({{ emitCss: false }})],
\tbuild: {{
\t\tlib: {{
\t\t\tentry: resolve(__dirname, 'src/index.ts'),
\t\t\tname: '{component}Ext',
\t\t\tformats: ['es'],
\t\t\tfileName: () => 'index.js',
\t\t}},
\t\trollupOptions: {{
\t\t\toutput: {{
\t\t\t\tinlineDynamicImports: true,
\t\t\t}},
\t\t}},
\t\tcssCodeSplit: false,
\t\tminify: 'esbuild',
\t\tsourcemap: false,
\t\ttarget: 'es2020',
\t\temptyOutDir: true,
\t}},
}});
""")

    with open(os.path.join(rt_dir, "tsconfig.json"), "w") as f:
        json.dump({
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "isolatedModules": True,
                "verbatimModuleSyntax": True,
                "allowSyntheticDefaultImports": True,
                "resolveJsonModule": True,
                "types": ["svelte"],
            },
            "include": ["src/**/*", "vite.config.ts"],
        }, f, indent=2)
        f.write("\n")

    with open(os.path.join(rt_dir, ".gitignore"), "w") as f:
        f.write("node_modules/\n*.log\n.vite/\n")

    with open(os.path.join(src_dir, "index.ts"), "w") as f:
        f.write(f"""import {{ mount, unmount }} from 'svelte';
import {component} from './{component}.svelte';

export interface RuntimeMountProps {{
\tbackend: any;
\textensionId: string;
\tversion: string;
\tprincipal?: string;
\tisAuthenticated?: boolean;
}}

export default function mountExt(target: HTMLElement, props: RuntimeMountProps) {{
\tconst component = mount({component}, {{ target, props }});
\treturn {{
\t\tunmount() {{
\t\t\ttry {{
\t\t\t\tunmount(component);
\t\t\t}} catch {{
\t\t\t\t/* already torn down */
\t\t\t}}
\t\t}},
\t}};
}}
""")

    print(f"  ✓ {ext_name} → {rt_dir}")


def main():
    if not os.path.isdir(EXTENSIONS_ROOT):
        print(f"Extensions root not found: {EXTENSIONS_ROOT}", file=sys.stderr)
        sys.exit(1)

    count = 0
    for name in sorted(os.listdir(EXTENSIONS_ROOT)):
        if name in SKIP:
            continue
        ext_dir = os.path.join(EXTENSIONS_ROOT, name)
        frontend_dir = os.path.join(ext_dir, "frontend")
        if os.path.isdir(frontend_dir):
            generate(name, ext_dir)
            count += 1

    print(f"\nGenerated boilerplate for {count} extensions.")


if __name__ == "__main__":
    main()
