import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from typing import Optional
import signal
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
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
        
        # Setup a signal handler for graceful shutdown on non-Windows systems or programmatic termination
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully by setting a flag."""
        self.console.print("\n🛑 [red]Termination signal received. Exiting gracefully...[/red]")
        self.running = False
    
    def display_current_time(self):
        """Display current system time with rich formatting."""
        current_time = datetime.now()
        
        time_table = Table(show_header=False, box=box.ROUNDED, expand=False)
        time_table.add_column("Info", style="cyan", width=20)
        time_table.add_column("Value", style="bright_white", width=30)
        
        time_table.add_row("🕐 Current Date", current_time.strftime("%A, %B %d, %Y"))
        time_table.add_row("⏰ Current Time", current_time.strftime("%I:%M:%S %p"))
        time_table.add_row("🌍 24-Hour Format", current_time.strftime("%H:%M:%S"))
        
        panel = Panel(
            time_table,
            title="[bold blue]🕒 System Time Information[/bold blue]",
            border_style="blue"
        )
        
        self.console.print(panel)
    
    def get_time_input(self) -> Optional[datetime]:
        """Interactive time selection with rich interface."""
        self.console.print("\n[bold yellow]⏰ Set Your Daily Trigger Time[/bold yellow]")
        
        format_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        format_table.add_column("Option", style="cyan")
        format_table.add_column("Description", style="white")
        format_table.add_row("1", "12-hour format (e.g., 7:30 AM)")
        format_table.add_row("2", "24-hour format (e.g., 07:30)")
        
        self.console.print(Panel(format_table, title="Time Format Options", border_style="green"))
        
        try:
            format_choice = IntPrompt.ask(
                "[bold green]Choose time format[/bold green]",
                choices=["1", "2"],
                default=1
            )
        except KeyboardInterrupt:
            self.console.print("\n[red]Operation cancelled.[/red]")
            return None
        
        if format_choice == 1:
            return self._get_12_hour_time()
        else:
            return self._get_24_hour_time()
    
    def _get_time_from_user(self, is_12_hour: bool) -> Optional[datetime]:
        """A unified function to get time input from the user."""
        prompt_style = "12-hour" if is_12_hour else "24-hour"
        self.console.print(f"\n[bold cyan]📝 Enter time in {prompt_style} format[/bold cyan]")
        
        while self.running:
            try:
                if is_12_hour:
                    hour = IntPrompt.ask("[green]Hour (1-12)[/green]", choices=[str(i) for i in range(1, 13)])
                else:
                    hour = IntPrompt.ask("[green]Hour (0-23)[/green]", choices=[str(i) for i in range(0, 24)])
                
                minute = IntPrompt.ask("[green]Minute (0-59)[/green]", choices=[str(i) for i in range(0, 60)], default=0)
                
                hour_24, display_time = hour, f"{hour:02d}:{minute:02d}"

                if is_12_hour:
                    period_choice = IntPrompt.ask("[green]Select period (1 for AM, 2 for PM)[/green]", choices=["1", "2"])
                    period = "AM" if period_choice == 1 else "PM"
                    display_time = f"{hour}:{minute:02d} {period}"
                    
                    if period == "AM" and hour == 12: hour_24 = 0
                    elif period == "PM" and hour != 12: hour_24 = hour + 12
                    else: hour_24 = hour

                now = datetime.now()
                scheduled_time = now.replace(hour=hour_24, minute=minute, second=0, microsecond=0)
                
                if scheduled_time <= now:
                    scheduled_time += timedelta(days=1)
                
                self._confirm_time_selection(scheduled_time, display_time)
                return scheduled_time
                
            except KeyboardInterrupt:
                self.console.print("\n[red]Operation cancelled.[/red]")
                return None
            except Exception as e:
                self.console.print(f"[red]Invalid input: {e}. Please try again.[/red]")
        return None

    def _get_12_hour_time(self) -> Optional[datetime]:
        return self._get_time_from_user(is_12_hour=True)

    def _get_24_hour_time(self) -> Optional[datetime]:
        return self._get_time_from_user(is_12_hour=False)

    def _confirm_time_selection(self, scheduled_time: datetime, display_time: str):
        """Confirm the selected time with the user."""
        confirmation_table = Table(show_header=False, box=box.ROUNDED)
        confirmation_table.add_column("Detail", style="cyan", no_wrap=True)
        confirmation_table.add_column("Value", style="bright_white")
        
        confirmation_table.add_row("⏰ Selected Time", display_time)
        confirmation_table.add_row("📅 Next Execution", scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p"))
        
        panel = Panel(
            confirmation_table,
            title="[bold green]✅ Time Confirmation[/bold green]",
            border_style="green"
        )
        self.console.print(panel)
    
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
            
            self.display_current_time()
            
            scheduled_time = self.get_time_input()
            if scheduled_time is None or not self.running:
                self.console.print("[yellow]No time scheduled. Exiting.[/yellow]")
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