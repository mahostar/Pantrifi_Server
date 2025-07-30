import os
import json
from typing import List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from rich.console import Console
from rich.table import Table
from rich import box
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize and return Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")  # or SUPABASE_SERVICE_ROLE_KEY for service role
    
    if not url or not key:
        raise ValueError("Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
    
    return create_client(url, key)

def get_subscription_priority(status: str) -> int:
    """Get priority for subscription status. Lower number = higher priority."""
    priority_map = {
        'active': 1,
        'past_due': 2,
        'expired': 3,
        'canceled': 4,
        'trialing': 5,
        'incomplete': 6,
        'incomplete_expired': 7,
        'unpaid': 8
    }
    return priority_map.get(status.lower(), 99)

def get_effective_subscription_status(subscription: Dict[str, Any]) -> str:
    """Get the effective subscription status, considering expiration dates."""
    if not subscription:
        return 'No Subscription'
    
    status = subscription['status']
    current_period_end = subscription.get('current_period_end')
    
    # If status is active or trialing, check if it's actually expired
    if status in ['active', 'trialing'] and current_period_end:
        try:
            end_date = datetime.fromisoformat(current_period_end.replace('Z', '+00:00'))
            now = datetime.now(end_date.tzinfo)
            
            if now > end_date:
                return 'expired'
        except:
            pass  # If date parsing fails, use original status
    
    return status

def fetch_users_with_subscriptions(supabase: Client) -> List[Dict[str, Any]]:
    """Fetch all users with their subscription data, prioritizing active subscriptions."""
    try:
        # Query users with their subscriptions using a LEFT JOIN approach
        # First get all users
        users_response = supabase.table("users").select("*").execute()
        users = users_response.data
        
        # Then get all subscriptions
        subscriptions_response = supabase.table("subscriptions").select("*").execute()
        subscriptions = subscriptions_response.data
        
        # Create a mapping of user_id to subscription data
        subscription_map = {}
        for sub in subscriptions:
            user_id = sub['user_id']
            if user_id not in subscription_map:
                subscription_map[user_id] = []
            subscription_map[user_id].append(sub)
        
        # Combine users with their subscription data
        combined_data = []
        for user in users:
            user_subs = subscription_map.get(user['id'], [])
            
            if user_subs:
                # User has subscriptions - prioritize by effective status
                # First, calculate effective status for each subscription
                for sub in user_subs:
                    sub['effective_status'] = get_effective_subscription_status(sub)
                
                # Sort subscriptions by priority (active first, then others)
                user_subs.sort(key=lambda x: (
                    get_subscription_priority(x['effective_status']),
                    -datetime.fromisoformat(x['created_at'].replace('Z', '+00:00')).timestamp()  # Newer first
                ), reverse=False)
                
                # Take only the highest priority subscription
                best_sub = user_subs[0]
                
                combined_data.append({
                    'user_id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'google_id': user['google_id'],
                    'has_claimed_trial': user['has_claimed_trial'],
                    'stripe_customer_id': user['stripe_customer_id'],
                    'user_created_at': user['created_at'],
                    'subscription_id': best_sub['id'],
                    'subscription_status': best_sub['effective_status'],  # Use effective status
                    'original_status': best_sub['status'],  # Keep original for reference
                    'stripe_subscription_id': best_sub['stripe_subscription_id'],
                    'current_period_start': best_sub['current_period_start'],
                    'current_period_end': best_sub['current_period_end'],
                    'trial_end': best_sub['trial_end'],
                    'subscription_created_at': best_sub['created_at']
                })
            else:
                # User has no subscriptions
                combined_data.append({
                    'user_id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'google_id': user['google_id'],
                    'has_claimed_trial': user['has_claimed_trial'],
                    'stripe_customer_id': user['stripe_customer_id'],
                    'user_created_at': user['created_at'],
                    'subscription_id': None,
                    'subscription_status': 'No Subscription',
                    'original_status': 'No Subscription',
                    'stripe_subscription_id': None,
                    'current_period_start': None,
                    'current_period_end': None,
                    'trial_end': None,
                    'subscription_created_at': None
                })
        
        return combined_data
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def format_datetime(dt_str: str) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_str

def create_users_table(data: List[Dict[str, Any]]) -> Table:
    """Create a Rich table with user and subscription data."""
    table = Table(
        title="Users and Subscription Status",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        show_lines=True
    )
    
    # Add columns
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Email", style="white")
    table.add_column("Has Trial", style="yellow", justify="center")
    table.add_column("Subscription Status", style="green", justify="center")
    table.add_column("Period Start", style="blue")
    table.add_column("Period End", style="blue")
    table.add_column("Trial End", style="red")
    table.add_column("User Created", style="dim")
    
    # Add rows
    for row in data:
        # Color code subscription status
        status = row['subscription_status']
        original_status = row.get('original_status', status)
        
        if status == 'active':
            status_style = "[green]Active[/green]"
        elif status == 'expired':
            # Show if it was originally active/trialing but is now expired
            if original_status in ['active', 'trialing']:
                status_style = "[red]Expired[/red] [dim](was " + original_status + ")[/dim]"
            else:
                status_style = "[red]Expired[/red]"
        elif status == 'canceled':
            status_style = "[red]Canceled[/red]"
        elif status == 'past_due':
            status_style = "[yellow]Past Due[/yellow]"
        elif status == 'trialing':
            status_style = "[blue]Trialing[/blue]"
        elif status == 'No Subscription':
            status_style = "[dim]No Subscription[/dim]"
        else:
            status_style = f"[white]{status.title()}[/white]"
        
        # Format trial claim status
        trial_claimed = "✓" if row['has_claimed_trial'] else "✗"
        
        table.add_row(
            row['name'],
            row['email'],
            trial_claimed,
            status_style,
            format_datetime(row['current_period_start']),
            format_datetime(row['current_period_end']),
            format_datetime(row['trial_end']),
            format_datetime(row['user_created_at'])
        )
    
    return table

def create_summary_table(data: List[Dict[str, Any]]) -> Table:
    """Create a summary table with subscription statistics."""
    table = Table(
        title="Subscription Summary",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Metric", style="white")
    table.add_column("Count", style="green", justify="right")
    
    # Calculate statistics
    total_users = len(set(row['user_id'] for row in data))
    active_subs = len([row for row in data if row['subscription_status'] == 'active'])
    expired_subs = len([row for row in data if row['subscription_status'] == 'expired'])
    canceled_subs = len([row for row in data if row['subscription_status'] == 'canceled'])
    trialing_subs = len([row for row in data if row['subscription_status'] == 'trialing'])
    past_due_subs = len([row for row in data if row['subscription_status'] == 'past_due'])
    no_subs = len([row for row in data if row['subscription_status'] == 'No Subscription'])
    claimed_trials = len([row for row in data if row['has_claimed_trial']])
    
    table.add_row("Total Users", str(total_users))
    table.add_row("Active Subscriptions", str(active_subs))
    table.add_row("Expired Subscriptions", str(expired_subs))
    table.add_row("Canceled Subscriptions", str(canceled_subs))
    table.add_row("Trialing Subscriptions", str(trialing_subs))
    table.add_row("Past Due Subscriptions", str(past_due_subs))
    table.add_row("No Subscriptions", str(no_subs))
    table.add_row("Claimed Trials", str(claimed_trials))
    
    return table

def export_to_json(data: List[Dict[str, Any]], filename: str = "extract_users_subscriptions.json"):
    """Export user and subscription data to JSON file."""
    # Calculate statistics for JSON
    total_users = len(set(row['user_id'] for row in data))
    active_subs = len([row for row in data if row['subscription_status'] == 'active'])
    expired_subs = len([row for row in data if row['subscription_status'] == 'expired'])
    canceled_subs = len([row for row in data if row['subscription_status'] == 'canceled'])
    trialing_subs = len([row for row in data if row['subscription_status'] == 'trialing'])
    past_due_subs = len([row for row in data if row['subscription_status'] == 'past_due'])
    no_subs = len([row for row in data if row['subscription_status'] == 'No Subscription'])
    claimed_trials = len([row for row in data if row['has_claimed_trial']])
    
    # Structure the JSON output
    json_output = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "total_records": len(data)
        },
        "summary": {
            "total_users": total_users,
            "active_subscriptions": active_subs,
            "expired_subscriptions": expired_subs,
            "canceled_subscriptions": canceled_subs,
            "trialing_subscriptions": trialing_subs,
            "past_due_subscriptions": past_due_subs,
            "no_subscriptions": no_subs,
            "claimed_trials": claimed_trials
        },
        "users": data
    }
    
    # Write to JSON file (overwrites existing file)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    return filename

def main():
    """Main function to extract and display user subscription data."""
    console = Console()
    
    try:
        # Initialize Supabase client
        console.print("[bold blue]Connecting to Supabase...[/bold blue]")
        supabase = get_supabase_client()
        
        # Fetch data
        console.print("[bold blue]Fetching user and subscription data...[/bold blue]")
        data = fetch_users_with_subscriptions(supabase)
        
        if not data:
            console.print("[red]No data found or error occurred.[/red]")
            return
        
        # Display summary
        console.print("\n")
        summary_table = create_summary_table(data)
        console.print(summary_table)
        
        # Display detailed table
        console.print("\n")
        users_table = create_users_table(data)
        console.print(users_table)
        
        # Export to JSON file
        console.print(f"\n[blue]Exporting data to JSON file...[/blue]")
        json_filename = export_to_json(data)
        console.print(f"[green]✓ Data exported to: {json_filename}[/green]")
        
        console.print(f"\n[green]Successfully retrieved data for {len(set(row['user_id'] for row in data))} users.[/green]")
        
    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        console.print("[yellow]Please create a .env file with your Supabase credentials:[/yellow]")
        console.print("SUPABASE_URL=your_supabase_url")
        console.print("SUPABASE_ANON_KEY=your_supabase_anon_key")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main() 