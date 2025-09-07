"""Deploy command for deploying realms to different networks."""

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

console = Console()


def deploy_command(
    config_file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Path to realm configuration file"
    ),
    folder: Optional[str] = typer.Option(
        None, "--folder", help="Path to generated realm folder with scripts"
    ),
    network: str = typer.Option(
        "local", "--network", "-n", help="Target network for deployment"
    ),
    clean: bool = typer.Option(
        False, "--clean", help="Clean deployment (restart dfx)"
    ),
) -> None:
    """Deploy a realm to the specified network."""
    console.print(f"[bold blue]🚀 Deploying Realm to {network}[/bold blue]\n")
    
    if folder:
        # Deploy using generated realm folder scripts
        console.print(f"📁 Using generated realm folder: {folder}")
        
        folder_path = Path(folder).resolve()
        if not folder_path.exists():
            console.print(f"[red]❌ Folder not found: {folder}[/red]")
            raise typer.Exit(1)
        
        scripts_dir = folder_path / "scripts"
        if not scripts_dir.exists():
            console.print(f"[red]❌ Scripts directory not found: {scripts_dir}[/red]")
            raise typer.Exit(1)
        
        # Run the three scripts in sequence
        scripts = [
            "1-install-extensions.sh",
            "2-deploy-canisters.sh", 
            "3-upload-data.sh"
        ]
        
        try:
            for script_name in scripts:
                script_path = scripts_dir / script_name
                if not script_path.exists():
                    console.print(f"[yellow]⚠️  Script not found: {script_path}[/yellow]")
                    continue
                
                console.print(f"🔧 Running {script_name}...")
                console.print(f"[dim]Script path: {script_path}[/dim]")
                console.print(f"[dim]Working directory: {Path.cwd()}[/dim]")
                
                # Make sure script is executable
                script_path.chmod(0o755)
                
                result = subprocess.run(
                    [str(script_path.resolve())],
                    cwd=Path.cwd(),
                    text=True
                )
                
                if result.returncode == 0:
                    console.print(f"[green]✅ {script_name} completed successfully[/green]")
                    if result.stdout:
                        console.print(result.stdout)
                else:
                    console.print(f"[red]❌ {script_name} failed[/red]")
                    if result.stderr:
                        console.print(f"[red]{result.stderr}[/red]")
                    if result.stdout:
                        console.print(result.stdout)
                    raise typer.Exit(1)
                
                console.print("")  # Add spacing between scripts
            
            console.print("[green]🎉 All deployment scripts completed successfully![/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error during script execution: {e}[/red]")
            raise typer.Exit(1)
    
    elif config_file:
        console.print(f"📄 Using config file: {config_file}")
        
        # Check if config file exists
        config_path = Path(config_file)
        if not config_path.exists():
            console.print(f"[red]❌ Config file not found: {config_file}[/red]")
            raise typer.Exit(1)
        
        # Config file deployment not yet implemented
        console.print(f"[yellow]⚠️  Config file deployment not yet implemented[/yellow]")
    
    else:
        # Default deployment using deploy_local.sh
        try:
            if network == "local":
                console.print("🔧 Running local deployment script...")
                result = subprocess.run(
                    ["./scripts/deploy_local.sh"],
                    cwd=Path.cwd(),
                    text=True
                )
                
                if result.returncode == 0:
                    console.print("[green]✅ Deployment completed successfully[/green]")
                    console.print(result.stdout)
                else:
                    console.print("[red]❌ Deployment failed[/red]")
                    console.print(f"[red]{result.stderr}[/red]")
                    raise typer.Exit(1)
            else:
                console.print(f"[yellow]⚠️  Network '{network}' deployment not yet implemented[/yellow]")
                console.print("[dim]Currently only 'local' network is supported[/dim]")
                
        except Exception as e:
            console.print(f"[red]❌ Error during deployment: {e}[/red]")
            raise typer.Exit(1)
