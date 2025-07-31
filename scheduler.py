import os
import sys
import time
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional
import signal
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich import box
from rich.align import Align

class PantrifiScheduler:
    def __init__(self):
        self.console = Console()
        self.scheduled_time = None
        self.running = True
        self.script_sequence = [
            "extract_users_subscriptions.py",
            "fetch_subscribed_users_data.py",
            "filter_users_with_sheets.py",
            "ai_pipeline_workflow.py"
        ]
        self.base_path = Path(__file__).resolve().parent
        self.config_file = self.base_path / "schedule_config.json"
        
        # Setup a signal handler for graceful shutdown on non-Windows systems or programmatic termination
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully by setting a flag."""
        self.console.print("\n🛑 [red]Termination signal received. Exiting gracefully...[/red]")
        self.running = False
    
    def load_schedule_config(self) -> Optional[datetime]:
        """Load the scheduled time from the JSON configuration file."""
        if not self.config_file.exists():
            self.console.print(f"[bold red]❌ Configuration file not found: {self.config_file}[/bold red]")
            self.console.print("[yellow]Please run 'python schedule_config.py' first to set up the schedule.[/yellow]")
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            hour = config_data['scheduled_hour']
            minute = config_data['scheduled_minute']
            
            now = datetime.now()
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the time has already passed today, schedule for tomorrow
            if scheduled_time <= now:
                scheduled_time += timedelta(days=1)
            
            # Display loaded configuration
            config_table = Table(show_header=False, box=box.ROUNDED)
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="bright_white")
            
            config_table.add_row("⏰ Scheduled Time", f"{hour:02d}:{minute:02d}")
            config_table.add_row("📅 Next Execution", scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p"))
            config_table.add_row("📝 Config Updated", config_data.get('last_updated', 'Unknown'))
            
            panel = Panel(
                config_table,
                title="[bold green]📋 Loaded Schedule Configuration[/bold green]",
                border_style="green"
            )
            self.console.print(panel)
            
            return scheduled_time
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Error loading configuration: {e}[/bold red]")
            self.console.print("[yellow]Please run 'python schedule_config.py' to fix the configuration.[/yellow]")
            return None
    
    def _get_time_until(self, target_time: datetime) -> str:
        """Calculate and format the time remaining until a target time."""
        delta = target_time - datetime.now()
        if delta.total_seconds() < 0:
            return "[yellow]Now executing...[/yellow]"
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0: parts.append(f"{days}d")
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}m")
        if not parts:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)
    
    def run_script_sequence(self):
        """
        Execute the script sequence, stopping immediately if a script fails.
        Forces child processes to use UTF-8 and displays their standard output on success.
        For ai_pipeline_workflow.py, shows real-time output instead of capturing it.
        """
        self.console.print("\n[bold yellow]🚀 Starting Script Sequence Execution...[/bold yellow]")
        
        success_count = 0
        scripts_attempted = 0
        
        child_env = os.environ.copy()
        child_env["PYTHONUTF8"] = "1"
        
        for i, script_name in enumerate(self.script_sequence, 1):
            scripts_attempted = i
            script_path = self.base_path / script_name
            self.console.rule(f"[bold blue]Step {i}/{len(self.script_sequence)}: Executing {script_name}[/bold blue]")
            
            if not script_path.exists():
                self.console.print(f"[red]❌ Error: Script not found at {script_path}[/red]")
                self.console.print("[bold red]Halting sequence.[/bold red]")
                break 

            start_time = time.time()
            try:
                # For ai_pipeline_workflow.py, show real-time output
                if script_name == "ai_pipeline_workflow.py":
                    self.console.print(f"[yellow]📺 Showing real-time output for {script_name}...[/yellow]")
                    result = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=str(self.base_path),
                        env=child_env,
                        encoding='utf-8',
                        errors='ignore'
                    )
                else:
                    # For other scripts, capture output to display after completion
                    result = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=str(self.base_path),
                        capture_output=True,
                        env=child_env,
                        encoding='utf-8',
                        errors='ignore'
                    )
                
                execution_time = time.time() - start_time
                
                if result.returncode == 0:
                    self.console.print(f"[green]✅ Success:[/green] {script_name} completed in {execution_time:.2f}s.")
                    success_count += 1
                    
                    # Only show captured output for non-AI pipeline scripts
                    if script_name != "ai_pipeline_workflow.py" and result.stdout and result.stdout.strip():
                        self.console.print(Panel(
                            Text(result.stdout, overflow="fold"),
                            title=f"[bold green]📋 Output from {script_name}[/bold green]",
                            border_style="green",
                            expand=False
                        ))

                else:
                    self.console.print(f"[bold red]❌ FAILURE: {script_name} failed with return code {result.returncode}.[/bold red]")
                    if hasattr(result, 'stderr') and result.stderr:
                        self.console.print(Panel(
                            Text(result.stderr, overflow="fold"),
                            title=f"[bold red]Error Output from {script_name}[/bold red]",
                            border_style="red"
                        ))
                    self.console.print("[bold red]Halting sequence due to error.[/bold red]")
                    break
            except Exception as e:
                self.console.print(f"[red]❌ CRITICAL ERROR executing {script_name}: {e}[/red]")
                self.console.print("[bold red]Halting sequence.[/bold red]")
                break
        
        self.console.rule("[bold green]Execution Summary[/bold green]")
        summary_table = Table(show_header=False, box=box.ROUNDED)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="bright_white")
        
        failed_count = scripts_attempted - success_count
        success_rate = (success_count / scripts_attempted * 100) if scripts_attempted > 0 else 0
        
        summary_table.add_row("✅ Successful Scripts", str(success_count))
        summary_table.add_row("❌ Failed Scripts", str(failed_count))
        summary_table.add_row("📊 Success Rate", f"{success_rate:.1f}%")
        self.console.print(summary_table)

    def generate_status_panel(self, scheduled_time: datetime):
        """Generates the rich Panel for the live status display."""
        now = datetime.now()
        time_until = self._get_time_until(scheduled_time)
        
        status_table = Table(show_header=False, box=box.ROUNDED)
        status_table.add_column("Status", style="cyan", width=20)
        status_table.add_column("Value", style="bright_white", width=35)
        
        status_table.add_row("🟢 Scheduler Status", "Running")
        status_table.add_row("⏰ Next Execution", scheduled_time.strftime("%Y-%m-%d %H:%M:%S"))
        status_table.add_row("⏳ Time Remaining", time_until)
        status_table.add_row("🕐 Current Time", now.strftime("%Y-%m-%d %H:%M:%S"))
        
        return Panel(
            status_table,
            title="[bold blue]📊 Pantrifi Scheduler Status[/bold blue]",
            subtitle="[dim]Press Ctrl+C to exit[/dim]",
            border_style="blue"
        )

    def run_scheduler_loop(self, scheduled_time: datetime):
        """Main scheduler loop using rich.Live for a smooth, flicker-free display."""
        self.console.print("\n[bold green]🔄 Scheduler is now running...[/bold green]")
        
        with Live(self.generate_status_panel(scheduled_time), console=self.console, screen=True, auto_refresh=False) as live:
            while self.running:
                now = datetime.now()
                
                if now >= scheduled_time:
                    live.stop()
                    self.console.rule(f"[bold yellow]🎯 Trigger time reached at {now.strftime('%H:%M:%S')}[/bold yellow]")
                    self.run_script_sequence()
                    
                    scheduled_time += timedelta(days=1)
                    self.console.print(f"\n[bold green]📅 Next execution scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold green]")
                    self.console.print("[dim]Resuming countdown...[/dim]")
                    time.sleep(5)
                    live.start()
                
                if not self.running:
                    break

                live.update(self.generate_status_panel(scheduled_time), refresh=True)
                time.sleep(1)
    
    def start(self):
        """Start the scheduler application."""
        try:
            welcome_text = Text("🍽️ PANTRIFI SCHEDULER 🍽️", style="bold magenta")
            self.console.print(Panel(Align.center(welcome_text), box=box.DOUBLE, border_style="magenta"))
            
            scheduled_time = self.load_schedule_config()
            if scheduled_time is None or not self.running:
                self.console.print("[yellow]No valid schedule configuration found. Exiting.[/yellow]")
                return
            
            self.scheduled_time = scheduled_time
            self.run_scheduler_loop(scheduled_time)
        
        except KeyboardInterrupt:
            self.console.print("\n[red]🛑 Scheduler stopped by user.[/red]")
        except Exception as e:
            self.console.print(f"\n[bold red]❌ A fatal error occurred: {e}[/bold red]")
        finally:
            self.console.print("[dim]👋 Goodbye![/dim]")

def main():
    """Main entry point"""
    scheduler = PantrifiScheduler()
    scheduler.start()

if __name__ == "__main__":
    main()