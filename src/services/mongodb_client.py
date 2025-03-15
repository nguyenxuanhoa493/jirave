import os
import streamlit as st
import pymongo
import ssl
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Hàm kiểm tra xem code có đang chạy trong Streamlit hay không
def is_running_in_streamlit():
    """Kiểm tra xem code có đang chạy trong môi trường Streamlit hay không"""
    try:
        # Nếu st.session_state có thể truy cập, thì chúng ta đang chạy trong Streamlit
        _ = st.session_state
        return True
    except:
        # Nếu không thể truy cập st.session_state, thì không phải Streamlit
        return False


class MongoDBClient:
    """Client kết nối đến MongoDB Atlas"""

    def __init__(self):
        """Khởi tạo kết nối đến MongoDB"""
        try:
            # Lấy URI kết nối từ biến môi trường hoặc sử dụng URI mặc định
            mongo_uri = os.environ.get("MONGODB_URI")

            if not mongo_uri:
                # Nếu không có MONGODB_URI, thử tạo từ DB_HOST và DB_PASSWORD
                db_host = os.environ.get("DB_HOST")
                db_password = os.environ.get("DB_PASSWORD")

                if not db_host or not db_password:
                    if is_running_in_streamlit():
                        st.warning(
                            "Thiếu thông tin kết nối MongoDB. Vui lòng kiểm tra biến môi trường MONGODB_URI hoặc DB_HOST và DB_PASSWORD"
                        )
                    self.client = None
                    self.db = None
                    return

                # Tạo URI không dùng SRV
                mongo_uri = f"mongodb://nguyenxuanhoa493:{db_password}@cluster0-shard-00-00.tpjip.mongodb.net:27017,cluster0-shard-00-01.tpjip.mongodb.net:27017,cluster0-shard-00-02.tpjip.mongodb.net:27017/data?ssl=true&replicaSet=atlas-blizro-shard-0&authSource=admin&retryWrites=true&w=majority"

            # Print connection info for debugging (hide password)
            debug_uri = mongo_uri.replace(os.environ.get("DB_PASSWORD", ""), "*****")
            print(f"Đang kết nối đến MongoDB với URI: {debug_uri}")

            # Sử dụng mặc định phương pháp #3
            connection_successful = False
            try:
                # Tạo URI không dùng SSL
                non_ssl_uri = mongo_uri.replace("ssl=true", "ssl=false")
                connection_options = {
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "serverSelectionTimeoutMS": 30000,
                }

                print("Đang kết nối với phương pháp #3...")
                self.client = pymongo.MongoClient(non_ssl_uri, **connection_options)
                self.client.admin.command("ping")  # Test connection
                self.db = self.client["data"]

                print("✅ Kết nối MongoDB thành công với phương pháp #3!")
                connection_successful = True
            except Exception as e:
                print(f"❌ Lỗi kết nối MongoDB với phương pháp #3: {str(e)}")

                # Nếu phương pháp #3 thất bại, thử phương pháp #1
                try:
                    # Tạo SSL context với các tùy chọn lỏng hơn
                    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    connection_options = {
                        "connectTimeoutMS": 30000,
                        "socketTimeoutMS": 30000,
                        "serverSelectionTimeoutMS": 30000,
                        "tlsAllowInvalidCertificates": True,
                        "tlsAllowInvalidHostnames": True,
                        "ssl_context": ssl_context,
                    }

                    print("Đang thử phương pháp kết nối #1...")
                    self.client = pymongo.MongoClient(mongo_uri, **connection_options)
                    self.client.admin.command("ping")  # Test connection
                    self.db = self.client["data"]

                    print("✅ Kết nối MongoDB thành công với phương pháp #1!")
                    connection_successful = True
                except Exception as e:
                    print(f"❌ Lỗi phương pháp kết nối #1: {str(e)}")

                    # Phương pháp 2: Thử với SSL cert_reqs=CERT_NONE thay vì ssl_context
                    try:
                        connection_options = {
                            "connectTimeoutMS": 30000,
                            "socketTimeoutMS": 30000,
                            "serverSelectionTimeoutMS": 30000,
                            "ssl": True,
                            "ssl_cert_reqs": ssl.CERT_NONE,
                        }

                        print("Đang thử phương pháp kết nối #2...")
                        self.client = pymongo.MongoClient(
                            mongo_uri, **connection_options
                        )
                        self.client.admin.command("ping")  # Test connection
                        self.db = self.client["data"]

                        print("✅ Kết nối MongoDB thành công với phương pháp #2!")
                        connection_successful = True
                    except Exception as e:
                        print(f"❌ Lỗi phương pháp kết nối #2: {str(e)}")

                        # Cuối cùng thất bại
                        self.client = None
                        self.db = None

                        if is_running_in_streamlit():
                            st.error(
                                f"Không thể kết nối đến MongoDB. Dữ liệu sẽ chỉ được lưu trên local. Lỗi: {str(e)}"
                            )
                        print(
                            f"❌ Không thể kết nối đến MongoDB sau khi thử tất cả các phương pháp: {str(e)}"
                        )

            if connection_successful and is_running_in_streamlit():
                st.success("✅ Đã kết nối thành công đến MongoDB!")

        except Exception as e:
            self.client = None
            self.db = None
            if is_running_in_streamlit():
                st.error(f"Lỗi không xác định khi kết nối MongoDB: {str(e)}")
            print(f"❌ Lỗi không xác định khi kết nối MongoDB: {str(e)}")

    def is_connected(self):
        """Kiểm tra xem đã kết nối đến MongoDB chưa"""
        try:
            # Kiểm tra kết nối bằng cách ping
            self.client.admin.command("ping")
            return True
        except Exception as e:
            if is_running_in_streamlit():
                st.error(f"Lỗi kết nối đến MongoDB: {str(e)}")
            print(f"Lỗi kết nối đến MongoDB: {str(e)}")
            return False

    def process_issues_data(self, issues, sprint_info=None):
        """Xử lý dữ liệu issues trước khi lưu để tránh phải xử lý lại sau này

        Args:
            issues (list): Danh sách issues gốc từ API
            sprint_info (dict, optional): Thông tin sprint

        Returns:
            list: Danh sách issues đã xử lý và sẵn sàng hiển thị
        """
        processed_issues = []

        # Định nghĩa danh sách các lập trình viên Full Stack
        fullstack_devs = [
            "Vũ Thanh Trung Anh",
            "Thuong Le",
            "Trường Nguyễn Bá",
            "Hán Văn Nam",
            "Thảo Phạm Văn",
            "Hùng Võ Văn",
            "Hoang Tran Van",
        ]

        # Định nghĩa danh sách các lập trình viên Frontend
        frontend_devs = ["Tran Toan Thang", "Nguyễn Nhật Minh", "Tú Trần Anh"]

        # Định nghĩa các trường cần thiết để lưu trữ cho mỗi issue
        required_fields = [
            "key",
            "summary",
            "issue_type",
            "status",
            "sprint_status",  # Thêm trường sprint_status
            "current_status",  # Thêm trường current_status
            "priority",
            "assignee",
            "group_dev",
            "is_subtask",
            "has_subtasks",
            "show_in_dashboard",
            "show_in_dashboard_final",
            "popup",
            "time_estimate",
            "steve_estimate",
            "time_spent",
            "sprint_time_spent",
            "remaining_time",
            "time_estimate_display",
            "steve_estimate_display",
            "time_spent_display",
            "sprint_time_spent_display",
            "remaining_time_display",
            "created",
            "updated",
            "dev_done_date",
            "test_done_date",
            "due_date",
            "completed",
            "url",
            "sprint_id",
            "sprint_name",
            "processed",
            "customer",
            "feature",
            "parent_key",
            "commits",
            "tester",
        ]

        # Lấy khoảng thời gian của sprint nếu có
        sprint_start = None
        sprint_end = None
        if sprint_info:
            if sprint_info.get("startDate"):
                sprint_start = datetime.fromisoformat(
                    sprint_info.get("startDate").replace("Z", "+00:00")
                )
            if sprint_info.get("endDate"):
                sprint_end = datetime.fromisoformat(
                    sprint_info.get("endDate").replace("Z", "+00:00")
                )

        for issue in issues:
            # Kiểm tra cấu trúc dữ liệu (MongoDB hoặc API)
            if "key" in issue and issue.get("processed", False):
                # Đã xử lý trước đó, chỉ lấy các trường cần thiết
                clean_issue = {
                    field: issue.get(field)
                    for field in required_fields
                    if field in issue
                }
                processed_issues.append(clean_issue)
                continue

            # Dữ liệu từ API Jira hoặc chưa được xử lý
            fields = issue.get("fields", {})
            issue_key = issue.get("key", "")

            # URL của issue
            issue_url = f"https://vieted.atlassian.net/browse/{issue_key}"

            # Xác định nếu issue là sub-task
            is_subtask = fields.get("issuetype", {}).get("subtask", False)

            # Xác định nếu issue có sub-task con
            has_subtasks = len(fields.get("subtasks", [])) > 0

            # Lấy giá trị của custom fields
            show_in_dashboard = "N/A"
            cf_dashboard = fields.get("customfield_10160", None)
            if (
                cf_dashboard
                and isinstance(cf_dashboard, dict)
                and "value" in cf_dashboard
            ):
                show_in_dashboard = cf_dashboard.get("value", "N/A")
            elif cf_dashboard:
                show_in_dashboard = str(cf_dashboard)

            # Chuyển đổi YES/NO sang True/False cho show_in_dashboard
            if show_in_dashboard == "YES":
                show_in_dashboard = True
            elif show_in_dashboard == "NO":
                show_in_dashboard = False

            popup = "N/A"
            cf_popup = fields.get("customfield_10130", None)
            if cf_popup and isinstance(cf_popup, dict) and "value" in cf_popup:
                popup = cf_popup.get("value", "N/A")
            elif cf_popup:
                popup = str(cf_popup)

            # Chuyển đổi YES/NO sang True/False cho popup
            if popup == "YES":
                popup = True
            elif popup == "NO":
                popup = False

            # Lấy thông tin Customer
            customer = "N/A"
            cf_customer = fields.get("customfield_10092", None)
            print(
                f"DEBUG - customfield_10092 (Customer) cho issue {issue_key}: {cf_customer}"
            )
            if cf_customer and isinstance(cf_customer, dict) and "value" in cf_customer:
                customer = cf_customer.get("value", "N/A")
            elif cf_customer:
                customer = str(cf_customer)
            print(f"DEBUG - Giá trị cuối cùng của Customer: {customer}")

            # Lấy thông tin Feature
            feature = "N/A"
            cf_feature = fields.get("customfield_10132", None)
            print(
                f"DEBUG - customfield_10132 (Feature) cho issue {issue_key}: {cf_feature}"
            )
            if cf_feature and isinstance(cf_feature, dict) and "value" in cf_feature:
                feature = cf_feature.get("value", "N/A")
            elif cf_feature:
                feature = str(cf_feature)
            print(f"DEBUG - Giá trị cuối cùng của Feature: {feature}")

            # Lấy parent key nếu issue là subtask
            parent_key = ""
            if is_subtask:
                parent_fields = fields.get("parent", {})
                parent_key = parent_fields.get("key", "")
                print(f"DEBUG - Issue cha của {issue_key}: {parent_key}")
            else:
                print(f"DEBUG - Issue {issue_key} không có issue cha")

            # Lấy thông tin Tester từ issue
            tester = issue.get("tester", "N/A")

            # Nếu không có tester trong issue, thử lấy từ customfield_10031
            if tester == "N/A" or not tester:
                cf_tester = fields.get("customfield_10031")
                if cf_tester:
                    if isinstance(cf_tester, dict) and "displayName" in cf_tester:
                        # Trường hợp tester là một user Jira
                        tester = cf_tester.get("displayName", "N/A")
                    elif isinstance(cf_tester, dict) and "value" in cf_tester:
                        # Trường hợp tester là một trường tùy chỉnh với giá trị
                        tester = cf_tester.get("value", "N/A")
                    elif isinstance(cf_tester, list) and len(cf_tester) > 0:
                        # Trường hợp tester là một danh sách (User Picker multiple users)
                        # Chỉ lấy người dùng đầu tiên trong danh sách
                        first_tester = cf_tester[0]
                        if (
                            isinstance(first_tester, dict)
                            and "displayName" in first_tester
                        ):
                            tester = first_tester.get("displayName", "N/A")
                        elif isinstance(first_tester, dict) and "value" in first_tester:
                            tester = first_tester.get("value", "N/A")
                        else:
                            tester = str(first_tester)
                    else:
                        # Trường hợp khác
                        tester = str(cf_tester)

            # Debug thông tin tester
            print(f"DEBUG - Tester cho issue {issue_key}: {tester}")

            # Lấy danh sách commit (giả sử từ một custom field hoặc liên kết Git)
            commits = []
            # Thêm logic lấy danh sách commit ở đây

            # Thông tin cơ bản
            summary = fields.get("summary", "")
            issue_type = fields.get("issuetype", {}).get("name", "")
            status = fields.get("status", {}).get("name", "")
            priority = fields.get("priority", {}).get("name", "")
            assignee = (
                fields.get("assignee", {}).get("displayName", "Unassigned")
                if fields.get("assignee")
                else "Unassigned"
            )

            # Đảm bảo trạng thái luôn là chuỗi hợp lệ
            status = (
                "Không xác định"
                if status is None or status == "None" or status == "null"
                else str(status)
            )

            # Xác định nhóm developer dựa trên assignee
            if assignee in fullstack_devs:
                dev_group = "DEV FULL"
            elif assignee in frontend_devs:
                dev_group = "DEV FE"
            else:
                dev_group = "NON DEV"

            # Xác định nhóm developer dựa trên assignee
            group_dev = "Full Stack" if assignee in fullstack_devs else "FE"

            # Thông tin thời gian
            created = fields.get("created", "")
            updated = fields.get("updated", "")
            due_date = fields.get("duedate", "")
            resolution_date = fields.get("resolutiondate", "")

            # Khởi tạo sprint_status với trạng thái hiện tại
            sprint_status = status

            # Xử lý changelog và trạng thái trong sprint
            changelog = issue.get("changelog", {}).get("histories", [])
            if changelog and sprint_start and sprint_end:
                status_changes = []
                for history in changelog:
                    try:
                        history_date = datetime.fromisoformat(
                            history.get("created", "").replace("Z", "+00:00")
                        )
                        if sprint_start <= history_date <= sprint_end:
                            for item in history.get("items", []):
                                if item.get("field") == "status" and item.get(
                                    "toString"
                                ):
                                    status_changes.append(
                                        {
                                            "date": history_date,
                                            "status": item.get("toString"),
                                        }
                                    )
                    except Exception:
                        continue

                if status_changes:
                    status_changes.sort(key=lambda x: x["date"])
                    sprint_status = status_changes[-1]["status"]

            # Xử lý Dev Done và Test Done dates
            dev_done_date = ""
            test_done_date = ""
            if changelog and sprint_start and sprint_end:
                for history in reversed(changelog):
                    try:
                        history_date = datetime.fromisoformat(
                            history.get("created", "").replace("Z", "+00:00")
                        )
                        if sprint_start <= history_date <= sprint_end:
                            for item in history.get("items", []):
                                if item.get("field") == "status":
                                    status_change = item.get("toString", "")
                                    if (
                                        status_change == "Test Done"
                                        and not test_done_date
                                    ):
                                        test_done_date = history.get("created", "")
                                    elif (
                                        status_change
                                        in ["Dev Done", "Deployed", "Done"]
                                        and not dev_done_date
                                    ):
                                        dev_done_date = history.get("created", "")
                    except Exception:
                        continue

            # Time tracking
            original_estimate_seconds = fields.get("timeoriginalestimate", 0) or 0
            remaining_estimate_seconds = fields.get("timeestimate", 0) or 0
            time_spent_seconds = fields.get("timespent", 0) or 0
            sprint_time_spent_seconds = 0

            # Tính toán thời gian trong sprint
            worklogs = fields.get("worklog", {}).get("worklogs", [])
            if worklogs and sprint_start and sprint_end:
                for worklog in worklogs:
                    try:
                        worklog_date = datetime.fromisoformat(
                            worklog.get("started", "").replace("Z", "+00:00")
                        )
                        if sprint_start <= worklog_date <= sprint_end:
                            sprint_time_spent_seconds += worklog.get(
                                "timeSpentSeconds", 0
                            )
                    except Exception:
                        continue

            # Chuyển đổi thời gian
            steve_estimate_hours = fields.get("customfield_10159", 0) or 0
            original_estimate_hours = original_estimate_seconds / 3600
            remaining_estimate_hours = remaining_estimate_seconds / 3600
            time_spent_hours = time_spent_seconds / 3600
            sprint_time_spent_hours = sprint_time_spent_seconds / 3600

            # Định dạng hiển thị
            original_estimate_display = self._format_time(original_estimate_seconds)
            remaining_estimate_display = self._format_time(remaining_estimate_seconds)
            time_spent_display = self._format_time(time_spent_seconds)
            sprint_time_spent_display = self._format_time(sprint_time_spent_seconds)
            steve_estimate_display = (
                f"{float(steve_estimate_hours):.2f}h"
                if steve_estimate_hours
                else "0.00h"
            )

            # Định dạng ngày tháng
            created_formatted = self._format_date(created)
            updated_formatted = self._format_date(updated)
            due_date_formatted = self._format_date(due_date)
            resolution_date_formatted = self._format_date(resolution_date)
            dev_done_date_formatted = self._format_date(dev_done_date)
            test_done_date_formatted = self._format_date(test_done_date)

            # Tạo processed issue
            processed_issue = {
                "key": issue_key,
                "summary": summary,
                "issue_type": issue_type,
                "status": sprint_status,
                "current_status": status,
                "priority": priority,
                "assignee": assignee,
                "dev_group": dev_group,
                "is_subtask": is_subtask,
                "has_subtasks": has_subtasks,
                "show_in_dashboard": show_in_dashboard,
                "popup": popup,
                "time_estimate": original_estimate_hours,
                "steve_estimate": steve_estimate_hours,
                "time_spent": time_spent_hours,
                "sprint_time_spent": sprint_time_spent_hours,
                "remaining_time": remaining_estimate_hours,
                "time_estimate_display": original_estimate_display,
                "steve_estimate_display": steve_estimate_display,
                "time_spent_display": time_spent_display,
                "sprint_time_spent_display": sprint_time_spent_display,
                "remaining_time_display": remaining_estimate_display,
                "created": created_formatted,
                "updated": updated_formatted,
                "dev_done_date": dev_done_date_formatted if dev_done_date else "N/A",
                "test_done_date": test_done_date_formatted if test_done_date else "N/A",
                "due_date": due_date_formatted if due_date else "N/A",
                "completed": resolution_date_formatted if resolution_date else "N/A",
                "url": issue_url,
                "sprint_id": issue.get("sprint_id", ""),
                "sprint_name": issue.get("sprint_name", ""),
                "customer": customer,
                "feature": feature,
                "parent_key": parent_key,
                "commits": commits,
                "tester": tester,
            }

            # Đảm bảo trạng thái là chuỗi hợp lệ
            processed_issue["status"] = (
                "Không xác định"
                if not processed_issue["status"]
                or processed_issue["status"] in ["None", "null"]
                else str(processed_issue["status"])
            )
            processed_issue["current_status"] = (
                "Không xác định"
                if not processed_issue["current_status"]
                or processed_issue["current_status"] in ["None", "null"]
                else str(processed_issue["current_status"])
            )

            # Tính toán show_in_dashboard_final
            is_epic = issue_type == "Epic"
            has_subtasks_bool = has_subtasks
            has_sprint_time = sprint_time_spent_seconds > 0
            dashboard_is_yes = show_in_dashboard is True
            is_excluded_assignee = assignee in [
                "Hoang Tran Van",
                "Unassigned",
                "Luyen Nguyen Thi",
            ]

            processed_issue["show_in_dashboard_final"] = not (
                is_epic
                or has_subtasks_bool
                or not has_sprint_time
                or not dashboard_is_yes
                or is_excluded_assignee
            )

            processed_issues.append(processed_issue)

        return processed_issues

    def _format_date(self, date_str):
        """Format ISO date string to a more readable format"""
        if not date_str:
            return ""

        try:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date_obj.strftime("%d/%m/%Y %H:%M")
        except:
            return date_str

    def _format_time(self, seconds):
        """Format time in seconds to hours with decimal (e.g., 3.50h)"""
        if not seconds:
            return "0.00h"

        # Quy đổi giây thành giờ (với phần thập phân)
        hours = seconds / 3600

        # Định dạng số giờ với 2 chữ số thập phân
        return f"{hours:.2f}h"

    def save_issues(self, issues, sprint_id, sprint_name, sprint_info=None):
        """Lưu danh sách issues đã xử lý vào MongoDB

        Args:
            issues (list): Danh sách issues đã xử lý
            sprint_id (str): ID của sprint
            sprint_name (str): Tên của sprint
            sprint_info (dict, optional): Thông tin chi tiết của sprint

        Returns:
            bool: True nếu lưu thành công, False nếu có lỗi
        """
        if not self.is_connected():
            if is_running_in_streamlit():
                st.warning("Chưa kết nối đến MongoDB. Không thể lưu dữ liệu.")
            return False

        try:
            # Sử dụng collection "data"
            collection = self.db["data"]

            print(f"Debug MongoDB save: Total issues: {len(issues)}")

            # Luôn xử lý lại dữ liệu trước khi lưu, bất kể đã xử lý trước đó hay chưa
            processed_issues = self.process_issues_data(issues, sprint_info)
            issues_to_save = processed_issues

            # Debug log sau khi xử lý
            if processed_issues and len(processed_issues) > 0:
                sample_processed = processed_issues[0]
                print(f"Sample after processing - Key: {sample_processed.get('key')}")
                print(
                    f"Status after processing: {sample_processed.get('status', 'Not set')}"
                )
                print(
                    f"Current status after processing: {sample_processed.get('current_status', 'Not set')}"
                )

            # Các trường cần thiết để lưu trữ vẫn được định nghĩa trong process_issues_data
            required_fields = [
                "key",
                "summary",
                "issue_type",
                "status",
                "current_status",
                "priority",
                "assignee",
                "dev_group",
                "is_subtask",
                "has_subtasks",
                "show_in_dashboard",
                "show_in_dashboard_final",
                "popup",
                "time_estimate",
                "steve_estimate",
                "time_spent",
                "sprint_time_spent",
                "remaining_time",
                "time_estimate_display",
                "steve_estimate_display",
                "time_spent_display",
                "sprint_time_spent_display",
                "remaining_time_display",
                "created",
                "updated",
                "dev_done_date",
                "test_done_date",
                "due_date",
                "completed",
                "url",
                "sprint_id",
                "sprint_name",
                "processed",
                "customer",
                "feature",
                "parent_key",
                "commits",
                "tester",
            ]
            issues_to_save = [
                {field: issue.get(field) for field in required_fields if field in issue}
                for issue in processed_issues
            ]

            # Xây dựng một document duy nhất chứa toàn bộ thông tin sprint và danh sách issues
            sprint_document = {
                "_id": f"sprint_{sprint_id}",
                "sprint_id": sprint_id,
                "sprint_name": sprint_name,
                "updated_at": datetime.now(),
                "total_issues": len(issues_to_save),
                "issues": issues_to_save,  # Lưu toàn bộ danh sách issues đã xử lý
            }

            # Thêm thông tin chi tiết của sprint nếu có
            if sprint_info:
                sprint_document["details"] = sprint_info

            # Lưu document vào MongoDB (upsert để ghi đè nếu đã tồn tại)
            collection.update_one(
                {"_id": sprint_document["_id"]},
                {"$set": sprint_document},
                upsert=True,
            )

            if is_running_in_streamlit():
                st.success(
                    f"Đã lưu sprint '{sprint_name}' với {len(issues_to_save)} issues vào MongoDB!"
                )
            return True
        except Exception as e:
            if is_running_in_streamlit():
                st.error(f"Lỗi khi lưu dữ liệu vào MongoDB: {str(e)}")
            return False

    def get_issues(self, sprint_id):
        """Lấy danh sách issues từ MongoDB

        Args:
            sprint_id (str): ID của sprint

        Returns:
            list: Danh sách issues, hoặc [] nếu không có
        """
        if not self.is_connected():
            if is_running_in_streamlit():
                st.warning("Chưa kết nối đến MongoDB. Không thể lấy dữ liệu.")
            return []

        try:
            # Sử dụng collection "data"
            collection = self.db["data"]

            # Tìm document sprint với _id tương ứng
            sprint_document = collection.find_one({"_id": f"sprint_{sprint_id}"})

            # Trả về danh sách issues trong document nếu tìm thấy
            if sprint_document and "issues" in sprint_document:
                return sprint_document["issues"]

            return []
        except Exception as e:
            if is_running_in_streamlit():
                st.error(f"Lỗi khi lấy dữ liệu từ MongoDB: {str(e)}")
            return []

    def get_sprint_info(self, sprint_id):
        """Lấy thông tin sprint từ MongoDB

        Args:
            sprint_id (str): ID của sprint

        Returns:
            dict: Thông tin sprint, hoặc None nếu không tìm thấy
        """
        if not self.is_connected():
            if is_running_in_streamlit():
                st.warning("Chưa kết nối đến MongoDB. Không thể lấy dữ liệu.")
            return None

        try:
            # Sử dụng collection "data"
            collection = self.db["data"]

            # Tìm document sprint với _id tương ứng
            sprint_document = collection.find_one(
                {"_id": f"sprint_{sprint_id}"},
                {"issues": 0},  # Loại bỏ trường issues để giảm kích thước response
            )

            # Trả về thông tin sprint nếu tìm thấy
            if sprint_document:
                return sprint_document

            return None
        except Exception as e:
            if is_running_in_streamlit():
                st.error(f"Lỗi khi lấy thông tin sprint từ MongoDB: {str(e)}")
            return None

    def get_all_sprints(self):
        """Lấy danh sách tất cả các sprints từ MongoDB

        Returns:
            list: Danh sách các thông tin sprint
        """
        if not self.is_connected():
            if is_running_in_streamlit():
                st.warning("Chưa kết nối đến MongoDB. Không thể lấy dữ liệu.")
            return []

        try:
            # Sử dụng collection "data"
            collection = self.db["data"]

            # Tìm tất cả các documents có _id bắt đầu bằng "sprint_"
            # Chỉ lấy các thông tin cơ bản (không lấy danh sách issues)
            sprint_list = list(
                collection.find(
                    {"_id": {"$regex": "^sprint_"}},
                    {
                        "issues": 0
                    },  # Loại trừ trường "issues" để giảm kích thước response
                ).sort("updated_at", -1)
            )

            return sprint_list
        except Exception as e:
            if is_running_in_streamlit():
                st.error(f"Lỗi khi lấy danh sách sprints từ MongoDB: {str(e)}")
            return []
