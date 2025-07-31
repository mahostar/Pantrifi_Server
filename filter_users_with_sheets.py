import json
import os

def filter_users_with_sheets_or_csv():
    # Read the input JSON file
    input_file = 'fetch_subscribed_users_data.json'
    output_file = 'filtered_users_with_sheets.json'
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {input_file}")
        return
    
    filtered_users = []
    
    # Filter users who have at least one Google Sheet OR CSV file (NOT menu files alone)
    for user in data.get('subscribed_users', []):
        google_sheets = user.get('google_sheets', [])
        menu_files = user.get('menu_files', [])
        csv_files = user.get('csv_files', [])
        
        # FIXED: Only include users with Google Sheets OR CSV files (inventory data)
        # Menu files alone are not sufficient for AI analysis
        if len(google_sheets) > 0 or len(csv_files) > 0:
            user_data = {
                'user_id': user.get('user_id', ''),  # Added user_id
                'name': user.get('name', ''),
                'email': user.get('email', ''),
                'google_sheets_urls': [],
                'csv_file_urls': [],
                'menu_file_urls': []
            }
            
            # Extract Google Sheets URLs (limit to 3 as specified)
            for sheet in google_sheets[:3]:
                sheet_url = sheet.get('sheet_url', '').strip()
                if sheet_url:
                    # Clean the URL by removing backticks and extra spaces
                    clean_url = sheet_url.strip('` ')
                    user_data['google_sheets_urls'].append(clean_url)
            
            # Extract CSV file URLs (limit to 3 as specified)
            for csv_file in csv_files[:3]:
                csv_url = csv_file.get('file_url', '').strip()
                if csv_url:
                    # Clean the URL by removing backticks and extra spaces
                    clean_url = csv_url.strip('` ')
                    user_data['csv_file_urls'].append({
                        'file_name': csv_file.get('file_name', ''),
                        'file_url': clean_url
                    })
            
            # Extract Menu file URLs (limit to 3 as specified)
            for menu in menu_files[:3]:
                menu_url = menu.get('file_url', '').strip()
                if menu_url:
                    # Clean the URL by removing backticks and extra spaces
                    clean_url = menu_url.strip('` ')
                    user_data['menu_file_urls'].append({
                        'file_name': menu.get('file_name', ''),
                        'file_url': clean_url
                    })
            
            # FIXED: Only add user if they have at least one valid sheet URL OR CSV URL
            # (Menu files are optional and will be included if available)
            if user_data['google_sheets_urls'] or user_data['csv_file_urls']:
                filtered_users.append(user_data)
    
    # Create output JSON structure
    output_data = {
        'filtered_users_count': len(filtered_users),
        'users_with_sheets_or_csv': filtered_users
    }
    
    # Write to output file (overwrite if exists)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully created {output_file} with {len(filtered_users)} users")
        print(f"Users included: {[user['name'] for user in filtered_users]}")
        
        # Additional logging for debugging
        if len(filtered_users) == 0:
            print("WARNING: No users found with Google Sheets or CSV files!")
        else:
            print(f"INFO: Filtered {len(filtered_users)} users with inventory data")
            
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")

if __name__ == "__main__":
    filter_users_with_sheets_or_csv()