# Supabase Users and Subscriptions Management Scripts

This repository contains two Python scripts for managing user and subscription data from Supabase:

1. **`extract_users_subscriptions.py`** - Extracts all users and their subscription states
2. **`fetch_subscribed_users_data.py`** - Fetches Google Sheets and menu data for subscribed/trialing users only

## Script 1: Extract Users and Subscriptions

This Python script connects to your Supabase database and extracts all users along with their subscription states, displaying the results in a beautiful table format using the Rich library.

## Features

- 📊 **Rich Table Display**: Beautiful, color-coded tables showing user and subscription data
- 📈 **Summary Statistics**: Quick overview of subscription metrics
- 🎨 **Color-coded Status**: Visual indicators for different subscription states
- 🔄 **Handles Multiple Subscriptions**: Supports users with multiple subscriptions
- ❌ **Handles Users Without Subscriptions**: Shows users who don't have any subscriptions
- 📄 **JSON Export**: Automatically exports data to `extract_users_subscriptions.json` file
- 🔄 **Auto-overwrite**: JSON file gets updated with fresh data on each run

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with your Supabase credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Alternative: Use service role key for admin access (recommended for scripts)
# SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Note**: For production scripts, it's recommended to use the `SUPABASE_SERVICE_ROLE_KEY` instead of the anon key for full access to your data.

### 3. Get Your Supabase Credentials

1. Go to your [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Go to Settings > API
4. Copy the URL and anon key (or service role key)

## Usage

Run the script:

```bash
python extract_users_subscriptions.py
```

**Output**: The script will display tables in the console AND automatically create/overwrite `extract_users_subscriptions.json` with the complete data.

## Output

The script displays two tables:

### 1. Subscription Summary
A quick overview showing:
- Total users
- Active subscriptions
- Canceled subscriptions  
- Trialing subscriptions
- Users without subscriptions
- Users who have claimed trials

### 2. Detailed Users Table
Shows each user with:
- **Name**: User's display name
- **Email**: User's email address
- **Has Trial**: Whether the user has claimed their trial (✓/✗)
- **Subscription Status**: Color-coded subscription state
  - 🟢 Active
  - 🔴 Canceled  
  - 🟡 Past Due
  - 🔵 Trialing
  - ⚪ No Subscription
- **Period Start/End**: Current billing period dates
- **Trial End**: When the trial expires
- **User Created**: When the user account was created

### 3. JSON Export File

The script automatically creates/overwrites `extract_users_subscriptions.json` with:

```json
{
  "export_info": {
    "timestamp": "2025-01-18T10:30:45.123456",
    "total_records": 4
  },
  "summary": {
    "total_users": 4,
    "active_subscriptions": 2,
    "expired_subscriptions": 0,
    "canceled_subscriptions": 0,
    "trialing_subscriptions": 1,
    "past_due_subscriptions": 0,
    "no_subscriptions": 1,
    "claimed_trials": 4
  },
  "users": [
    {
      "user_id": "abc123...",
      "name": "John Doe",
      "email": "john@example.com",
      "subscription_status": "active",
      "original_status": "active",
      "current_period_start": "2025-01-01T00:00:00Z",
      "current_period_end": "2025-02-01T00:00:00Z",
      // ... other fields
    }
  ]
}
```

## Database Schema

The script works with these Supabase tables:

### Users Table
```sql
create table public.users (
  id uuid not null default gen_random_uuid (),
  google_id character varying(255) not null,
  name character varying(255) not null,
  email character varying(255) not null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  has_claimed_trial boolean null default false,
  stripe_customer_id text null,
  constraint users_pkey primary key (id),
  constraint users_email_key unique (email),
  constraint users_google_id_key unique (google_id)
)
```

### Subscriptions Table
```sql
create table public.subscriptions (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  stripe_customer_id text not null,
  stripe_subscription_id text not null,
  status text not null,
  current_period_start timestamp with time zone null,
  current_period_end timestamp with time zone null,
  trial_end timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint subscriptions_pkey primary key (id),
  constraint subscriptions_stripe_subscription_id_key unique (stripe_subscription_id),
  constraint subscriptions_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
)
```

## Troubleshooting

### Common Issues

1. **"Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables"**
   - Make sure you have a `.env` file with the correct credentials

2. **Permission denied errors**
   - Try using the `SUPABASE_SERVICE_ROLE_KEY` instead of the anon key
   - Check your Row Level Security (RLS) policies in Supabase

3. **No data found**
   - Verify your database has users and/or subscriptions data
   - Check your Supabase connection and table names

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Use environment variables or secure secret management for production deployments
- The service role key has full access to your database - use with caution 