import datetime
from jira_client import JiraClient
from tabulate import tabulate
from datetime import datetime, timedelta

class WorklogReport:
    def __init__(self):
        self.jira = JiraClient()

    def get_project_worklogs(self, start_date=None, end_date=None):
        jql = f'project = CLD AND worklogDate >= "{start_date}"'
        if end_date:
            jql += f' AND worklogDate <= "{end_date}"'

        response = self.jira.get(
            "search",
            params={
                "jql": jql,
                "fields": "worklog,summary,assignee",
                "maxResults": 1000
            }
        )

        if response.status_code != 200:
            return None

        return self._process_worklogs(response.json()["issues"], start_date, end_date)

    def _process_worklogs(self, issues, start_date, end_date):
        worklog_data = {
            'by_user': {},
            'by_issue': {},
            'daily_summary': {},
            'total_hours': 0
        }

        for issue in issues:
            worklog_response = self.jira.get(f"issue/{issue['id']}/worklog")
            if worklog_response.status_code != 200:
                continue

            issue_key = issue['key']
            worklog_data['by_issue'][issue_key] = {
                'summary': issue['fields']['summary'],
                'worklogs': []
            }

            for worklog in worklog_response.json()["worklogs"]:
                worklog_date = worklog["started"][:10]
                if start_date <= worklog_date <= end_date:
                    author = worklog["author"]["displayName"]
                    time_spent_hours = worklog["timeSpentSeconds"] / 3600
                    
                    # By user
                    if author not in worklog_data['by_user']:
                        worklog_data['by_user'][author] = 0
                    worklog_data['by_user'][author] += time_spent_hours

                    # By issue with detailed worklog
                    worklog_data['by_issue'][issue_key]['worklogs'].append({
                        'author': author,
                        'date': worklog_date,
                        'hours': time_spent_hours
                    })

                    # Daily summary
                    if worklog_date not in worklog_data['daily_summary']:
                        worklog_data['daily_summary'][worklog_date] = {}
                    if author not in worklog_data['daily_summary'][worklog_date]:
                        worklog_data['daily_summary'][worklog_date][author] = 0
                    worklog_data['daily_summary'][worklog_date][author] += time_spent_hours

                    worklog_data['total_hours'] += time_spent_hours

        return worklog_data

    def display_report(self, start_date=None, end_date=None):
        data = self.get_project_worklogs(start_date, end_date)
        if not data:
            return

        print(f"\n📊 Worklog Report for CLD Project")
        print(f"Period: {start_date} to {end_date}\n")

        # User Summary
        print("\n👥 Hours by Team Member:")
        user_table = [[user, f"{hours:.2f}"] for user, hours in data['by_user'].items()]
        print(tabulate(user_table, headers=['Team Member', 'Hours'], tablefmt='grid'))

        # Issue Summary
        print("\n📋 Hours by Issue:")
        issue_table = [[key, data['by_issue'][key]['summary'], f"{data['by_issue'][key]['hours']:.2f}"] 
                      for key in data['by_issue']]
        print(tabulate(issue_table, headers=['Issue', 'Summary', 'Hours'], tablefmt='grid'))

        # Daily Summary
        print("\n📅 Daily Summary:")
        dates = sorted(data['daily_summary'].keys())
        users = sorted(data['by_user'].keys())
        daily_table = []
        for date in dates:
            row = [date]
            for user in users:
                row.append(f"{data['daily_summary'][date].get(user, 0):.2f}")
            daily_table.append(row)
        print(tabulate(daily_table, headers=['Date'] + users, tablefmt='grid'))

        print(f"\n📈 Total Hours: {data['total_hours']:.2f}")