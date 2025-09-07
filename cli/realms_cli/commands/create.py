"""Create command for generating new realms with demo data and deployment scripts."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()


def create_command(
    random: bool,
    citizens: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
    output_dir: str,
    realm_name: str,
    network: str,
    deploy: bool,
) -> None:
    """Create a new realm with optional realistic demo data and deployment scripts."""
    console.print(f"[bold blue]🏛️  Creating Realm: {realm_name}[/bold blue]\n")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create scripts subdirectory
    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    console.print(f"📁 Output directory: {output_path.absolute()}")
    console.print(f"📁 Scripts directory: {scripts_dir.absolute()}")
    
    if random:
        console.print(f"🎲 Generating random data...")
        console.print(f"   👥 Citizens: {citizens}")
        console.print(f"   🏢 Organizations: {organizations}")
        console.print(f"   💰 Transactions: {transactions}")
        console.print(f"   ⚖️  Disputes: {disputes}")
        if seed:
            console.print(f"   🌱 Seed: {seed}")
        
        # Call the realm_generator.py script
        try:
            cmd = [
                sys.executable,
                "scripts/realm_generator.py",
                "--citizens", str(citizens),
                "--organizations", str(organizations),
                "--transactions", str(transactions),
                "--disputes", str(disputes),
                "--output-dir", str(output_path),
                "--realm-name", realm_name,
            ]
            
            if seed:
                cmd.extend(["--seed", str(seed)])
            
            console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode != 0:
                console.print(f"[red]❌ Error generating realm data:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                if result.stdout:
                    console.print(f"Output: {result.stdout}")
                raise typer.Exit(1)
            
            console.print("[green]✅ Realm data generated successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error running realm generator: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("📋 Creating empty realm structure...")
        
        # Create minimal realm data structure
        minimal_data = []
        
        # Save minimal data
        json_file = output_path / "realm_data.json"
        with open(json_file, 'w') as f:
            json.dump(minimal_data, f, indent=2)
        
        console.print(f"✅ Empty realm structure created")
    
    # Copy deployment scripts from existing files
    console.print("\n🔧 Copying deployment scripts...")
    
    # Get the project root directory (assuming we're in cli/ subdirectory)
    project_root = Path.cwd()
    
    # 1. Copy install_extensions.sh as 1-install-extensions.sh
    source_install = project_root / "scripts" / "install_extensions.sh"
    target_install = scripts_dir / "1-install-extensions.sh"
    if source_install.exists():
        shutil.copy2(source_install, target_install)
        target_install.chmod(0o755)
        console.print(f"   ✅ {target_install.name}")
    else:
        console.print(f"   ❌ Source file not found: {source_install}")
    
    # 2. Copy deploy_local.sh as 2-deploy-canisters.sh
    source_deploy = project_root / "scripts" / "deploy_local.sh"
    target_deploy = scripts_dir / "2-deploy-canisters.sh"
    if source_deploy.exists():
        shutil.copy2(source_deploy, target_deploy)
        target_deploy.chmod(0o755)
        console.print(f"   ✅ {target_deploy.name}")
    else:
        console.print(f"   ❌ Source file not found: {source_deploy}")
    
    # 3. Create a simple upload data script
    upload_script_content = f'''#!/bin/bash
set -e

echo "📥 Uploading realm data..."
realms import realm_data.json

echo "📜 Uploading codex files..."
for codex_file in *_codex.py; do
    if [ -f "$codex_file" ]; then
        echo "  Importing $(basename $codex_file)..."
        realms import "$codex_file" --type codex
    fi
done

echo "✅ Data upload completed!"
'''
    
    upload_script = scripts_dir / "3-upload-data.sh"
    upload_script.write_text(upload_script_content)
    upload_script.chmod(0o755)
    console.print(f"   ✅ {upload_script.name}")
    
    console.print(f"\n[green]🎉 Realm '{realm_name}' created successfully![/green]")
    console.print(f"\n[bold]Next Steps:[/bold]")
    console.print(f"realms deploy --folder {output_dir}")
    
    
    if deploy:
        console.print(f"\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        console.print(f"[dim]Note: Auto-deployment not yet implemented. Please run the scripts manually.[/dim]")
