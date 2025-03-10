import datetime
from jira_client import JiraClient
from tabulate import tabulate

def get_sprint_worklogs(date=None, show_details=False):
    jira = JiraClient()
    
    # Prepare JQL based on date
    if date:
        jql = f'project = CLOUD AND sprint in ("CLOUD Sprint 9") AND worklogDate = "{date}"'
    else:  # full sprint
        jql = 'project = CLOUD AND sprint in ("CLOUD Sprint 9")'
    
    # Get issues from specific sprint by name
    response = jira.get(
        "search",
        params={
            "jql": jql,
            "fields": "worklog,summary"
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Error fetching issues: {response.status_code}")
        return
    
    issues = response.json()["issues"]
    
    # Process worklogs
    worklog_stats = {}
    total_hours = 0
    detailed_logs = {}
    
    for issue in issues:
        worklog_response = jira.get(f"issue/{issue['id']}/worklog")
        
        if worklog_response.status_code == 200:
            worklogs = worklog_response.json()["worklogs"]
            for worklog in worklogs:
                # Only process worklog if it matches the specified date
                worklog_date = datetime.datetime.strptime(
                    worklog["started"][:10], 
                    "%Y-%m-%d"
                ).strftime("%Y-%m-%d")
                
                if date and worklog_date != date:
                    continue
                    
                author = worklog["author"]["displayName"]
                time_spent_seconds = worklog["timeSpentSeconds"]
                time_spent_hours = time_spent_seconds / 3600
                
                if author not in worklog_stats:
                    worklog_stats[author] = 0
                    detailed_logs[author] = {}
                
                worklog_stats[author] += time_spent_hours
                total_hours += time_spent_hours
                
                if show_details:
                    issue_key = issue['key']
                    if issue_key not in detailed_logs[author]:
                        detailed_logs[author][issue_key] = {
                            'Issue Key': issue_key,
                            'Summary': issue['fields']['summary'],
                            'Hours': 0
                        }
                    detailed_logs[author][issue_key]['Hours'] += round(time_spent_hours, 2)
    # Update the statistics header
    print(f"\n📊 Work Log Statistics for CLOUD Sprint 9 - {date if date else 'Full Sprint'}")
    print("\nTime spent by team members:")
    for author, hours in worklog_stats.items():
        print(f"- {author}: {hours:.2f} hours")
        if show_details and detailed_logs[author]:
            print("\nDetailed Worklog:")
            # Convert dictionary to list for tabulate
            table_data = list(detailed_logs[author].values())
            print(tabulate(table_data, headers="keys", tablefmt="grid"))
        print("\n")
    print(f"Total hours logged: {total_hours:.2f}")

if __name__ == "__main__":
    # Example: Get worklogs for a specific date
    
    get_sprint_worklogs(date="2025-02-28", show_details=True)