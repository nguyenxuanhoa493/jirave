import streamlit as st
import pymongo
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import tempfile
from sshtunnel import SSHTunnelForwarder
import pandas as pd
import plotly.express as px
import json

# Load environment variables
load_dotenv()

# Thiết lập trang
st.set_page_config(page_title="Video HLS", page_icon="🎥", layout="wide")

# Tạo tabs với icon
tab1, tab2 = st.tabs(["🎞 Thống kê", "🎬 Chi tiết Video"])


def process_video_data(video):
    """Xử lý dữ liệu video để hiển thị"""
    processed_data = {}

    # Lấy thông tin từ info
    if "info" in video:
        info = video["info"]
        processed_data.update(
            {
                "extension": info.get("extension", "N/A"),
                "fileName": info.get("fileName", "N/A"),
                "size": info.get("size", "0"),
                "duration": info.get("duration", "0"),
                "bitRate": info.get("bitRate", "0"),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "codeName": info.get("codeName", "N/A"),
                "frameRate": info.get("frameRate", "N/A"),
            }
        )

    # Lấy thông tin từ params
    if "params" in video:
        params = video["params"]
        processed_data.update(
            {
                "link_mp4": params.get("downloadUrl", "N/A"),
                "dmn": params.get("requestBody", {}).get("_sand_domain", "N/A"),
                "drm": params.get("isDrm", False),
            }
        )

    # Lấy các trường khác
    processed_data.update(
        {
            "status": video.get("status", 0),
            "created_at": video.get("created_at", "N/A"),
            "updated_at": video.get("updated_at", "N/A"),
            "responseStatus": video.get("responseStatus", "N/A"),
            "hlsUrl": video.get("hlsUrl", "N/A"),
        }
    )

    return processed_data


def display_video_player(video_data):
    """Hiển thị video player với nút chuyển đổi giữa HLS và MP4"""
    hls_url = video_data.get("hlsUrl")
    mp4_url = video_data.get("link_mp4")

    if hls_url or mp4_url:
        # Tạo container cho video player
        video_container = st.container()

        # Tạo radio buttons để chọn định dạng video với key cố định
        format_choice = st.radio(
            "Chọn định dạng video",
            (
                ["MP4", "HLS (m3u8)"]
                if hls_url and mp4_url
                else ["MP4"] if mp4_url else ["HLS (m3u8)"]
            ),
            horizontal=True,
            key=f"video_format_{video_data.get('fileID', 'default')}",
        )

        # Hiển thị video player theo định dạng đã chọn
        with video_container:
            if format_choice == "MP4" and mp4_url:
                st.video(mp4_url)
            elif format_choice == "HLS (m3u8)" and hls_url:
                # Hiển thị video player m3u8 bằng iframe
                st.markdown(
                    f"""
                    <iframe 
                        src="https://www.hlsplayer.net/embed?type=m3u8&src={hls_url}"
                        style="width: 100%; max-width: 854px; height: 480px; border: none;"
                        allowfullscreen>
                    </iframe>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.warning("Không có URL video để phát")


# Tab 1: Thống kê
with tab1:
    st.title("🎞 Video HLS Management")

    # Tạo bộ lọc ngày tháng dạng date range
    today = datetime.now()
    first_day_of_month = today.replace(day=1)
    if today.month == 12:
        last_day_of_month = today.replace(
            year=today.year + 1, month=1, day=1
        ) - timedelta(days=1)
    else:
        last_day_of_month = today.replace(month=today.month + 1, day=1) - timedelta(
            days=1
        )
    last_day_of_month = min(last_day_of_month, today)

    # Tạo layout 2 cột cho bộ lọc
    col1, col2 = st.columns(2)

    with col1:
        # Sử dụng date_input với key để tránh lỗi khi chọn nhiều tháng
        date_range = st.date_input(
            "Chọn khoảng thời gian",
            value=(first_day_of_month.date(), last_day_of_month.date()),
            max_value=today.date(),
            key="date_range",
        )

    with col2:
        # Thêm bộ lọc trạng thái
        status_filter = st.selectbox(
            "Chọn trạng thái", ["Tất cả", "Thành công", "Lỗi"], key="status_filter"
        )

    # Xử lý date range
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        # Chỉ xử lý khi đã chọn cả 2 ngày
        if start_date and end_date:
            # Kết nối MongoDB
            try:
                # Đọc thông tin kết nối từ .env
                SSH_HOST = os.getenv("SSH_HOST")
                SSH_USER = os.getenv("SSH_USER")
                SSH_KEY = os.getenv("SSH_KEY")
                DB_NAME = "vieted_hls"
                COLLECTION_NAME = "files"

                # Tạo file tạm thời chứa SSH key
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_key:
                    temp_key.write(SSH_KEY)
                    temp_key_path = temp_key.name

                # Tạo SSH tunnel
                with SSHTunnelForwarder(
                    (SSH_HOST, 22),
                    ssh_username=SSH_USER,
                    ssh_pkey=temp_key_path,
                    remote_bind_address=("127.0.0.1", 27017),
                ) as tunnel:
                    # Kết nối MongoDB thông qua SSH tunnel
                    client = pymongo.MongoClient(
                        f"mongodb://127.0.0.1:{tunnel.local_bind_port}/{DB_NAME}"
                    )

                    # Chọn database và collection
                    db = client[DB_NAME]
                    collection = db[COLLECTION_NAME]

                    # Hiển thị thông báo kết nối thành công
                    st.success("Kết nối MongoDB thành công!")

                    # Chuyển đổi ngày tháng sang datetime
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    end_datetime = datetime.combine(end_date, datetime.max.time())

                    # Tạo query cơ bản với bộ lọc ngày tháng
                    query = {
                        "created_at": {"$gte": start_datetime, "$lte": end_datetime}
                    }

                    # Thêm điều kiện lọc theo trạng thái nếu được chọn
                    if status_filter == "Thành công":
                        query["status"] = 1
                    elif status_filter == "Lỗi":
                        query["status"] = {"$ne": 1}

                    # Lấy tất cả bản ghi
                    records = list(collection.find(query))

                    # Chuyển đổi dữ liệu thành DataFrame
                    if records:
                        # Xử lý dữ liệu
                        processed_records = [
                            process_video_data(record) for record in records
                        ]
                        df = pd.DataFrame(processed_records)

                        # Chuyển đổi datetime thành string
                        if "created_at" in df.columns:
                            df["created_at"] = pd.to_datetime(df["created_at"])
                            df["date"] = df["created_at"].dt.date
                            df["created_at"] = df["created_at"].dt.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        if "updated_at" in df.columns:
                            df["updated_at"] = pd.to_datetime(
                                df["updated_at"]
                            ).dt.strftime("%Y-%m-%d %H:%M:%S")

                        # Lấy status trực tiếp từ records gốc và chuyển đổi thành label
                        df["status"] = [record.get("status", 0) for record in records]
                        df["status_label"] = df["status"].apply(
                            lambda x: "Thành công" if x == 1 else "Lỗi"
                        )

                        # Lọc theo status_label nếu được chọn
                        if status_filter != "Tất cả":
                            if status_filter == "Thành công":
                                df = df[df["status"] == 1]
                            else:  # Lỗi
                                df = df[df["status"] != 1]

                        # Tính toán thống kê status
                        total_records = len(df)
                        success_records = len(df[df["status"] == 1])
                        error_records = total_records - success_records

                        # Hiển thị thống kê
                        st.subheader("Thống kê")
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            st.metric("Tổng số bản ghi", total_records)
                        with col2:
                            st.metric("Video thành công", success_records)
                        with col3:
                            st.metric("Video lỗi", error_records)
                        with col4:
                            if "size" in df.columns and not df["size"].isna().all():
                                total_size = df["size"].astype(float).sum()
                                st.metric(
                                    "Tổng dung lượng (GB)",
                                    f"{total_size/1024/1024/1024:.2f}",
                                )
                            else:
                                st.metric("Tổng dung lượng (GB)", "N/A")
                        with col5:
                            if (
                                "duration" in df.columns
                                and not df["duration"].isna().all()
                            ):
                                total_duration = df["duration"].astype(float).sum()
                                st.metric(
                                    "Tổng thời lượng (giờ)",
                                    f"{total_duration/3600:.2f}",
                                )
                            else:
                                st.metric("Tổng thời lượng (giờ)", "N/A")

                        # Tạo biểu đồ xếp chồng theo ngày
                        st.subheader("Thống kê theo ngày")
                        daily_stats = (
                            df.groupby(["date", "status_label"])
                            .size()
                            .reset_index(name="count")
                        )

                        fig = px.bar(
                            daily_stats,
                            x="date",
                            y="count",
                            color="status_label",
                            title="Số lượng video theo trạng thái và ngày",
                            labels={
                                "count": "Số lượng",
                                "date": "Ngày",
                                "status_label": "Trạng thái",
                            },
                            barmode="stack",
                            color_discrete_map={
                                "Thành công": "rgb(0, 104, 201)",
                                "Lỗi": "#FF0000",
                            },
                        )

                        fig.update_layout(
                            xaxis_title="Ngày",
                            yaxis_title="Số lượng video",
                            legend_title="Trạng thái",
                            showlegend=True,
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        # Thêm các biểu đồ thống kê mới
                        st.subheader("Thống kê chi tiết")

                        # 1. Phân bố theo status
                        col1, col2 = st.columns(2)
                        with col1:
                            status_counts = df["status_label"].value_counts()
                            fig_status = px.pie(
                                values=status_counts.values,
                                names=status_counts.index,
                                title="Phân bố theo trạng thái",
                                hole=0.4,
                                color_discrete_map={
                                    "Thành công": "rgb(0, 104, 201)",
                                    "Lỗi": "#FF0000",
                                },
                            )
                            st.plotly_chart(fig_status, use_container_width=True)

                        # 2. Phân bố theo size (gap 100MB)
                        with col2:
                            if "size" in df.columns and not df["size"].isna().all():
                                df["size_mb"] = df["size"].astype(float) / (1024 * 1024)
                                df["size_range"] = pd.cut(
                                    df["size_mb"],
                                    bins=[
                                        0,
                                        100,
                                        200,
                                        300,
                                        400,
                                        500,
                                        600,
                                        700,
                                        800,
                                        900,
                                        1000,
                                        float("inf"),
                                    ],
                                    labels=[
                                        "0-100MB",
                                        "100-200MB",
                                        "200-300MB",
                                        "300-400MB",
                                        "400-500MB",
                                        "500-600MB",
                                        "600-700MB",
                                        "700-800MB",
                                        "800-900MB",
                                        "900-1000MB",
                                        ">1000MB",
                                    ],
                                )
                                size_counts = (
                                    df["size_range"].value_counts().sort_index()
                                )
                                fig_size = px.bar(
                                    x=size_counts.index,
                                    y=size_counts.values,
                                    title="Phân bố theo dung lượng (gap 100MB)",
                                    labels={"x": "Dung lượng", "y": "Số lượng"},
                                )
                                fig_size.update_layout(xaxis_tickangle=45)
                                st.plotly_chart(fig_size, use_container_width=True)
                            else:
                                st.warning("Không có thông tin về dung lượng")

                        # 3. Phân bố theo độ phân giải
                        col3, col4 = st.columns(2)
                        with col3:
                            if (
                                "width" in df.columns
                                and "height" in df.columns
                                and not df["width"].isna().all()
                                and not df["height"].isna().all()
                            ):
                                df["resolution"] = (
                                    df["width"].astype(str)
                                    + "x"
                                    + df["height"].astype(str)
                                )
                                resolution_counts = (
                                    df["resolution"].value_counts().head(10)
                                )
                                fig_res = px.bar(
                                    x=resolution_counts.index,
                                    y=resolution_counts.values,
                                    title="Top 10 độ phân giải phổ biến",
                                    labels={"x": "Độ phân giải", "y": "Số lượng"},
                                )
                                st.plotly_chart(fig_res, use_container_width=True)
                            else:
                                st.warning("Không có thông tin về độ phân giải")

                        # 4. Phân bố theo codec
                        with col4:
                            if (
                                "codeName" in df.columns
                                and not df["codeName"].isna().all()
                            ):
                                codec_counts = df["codeName"].value_counts().head(10)
                                fig_codec = px.pie(
                                    values=codec_counts.values,
                                    names=codec_counts.index,
                                    title="Top 10 codec phổ biến",
                                    hole=0.4,
                                )
                                st.plotly_chart(fig_codec, use_container_width=True)
                            else:
                                st.warning("Không có thông tin về codec")

                        # 5. Phân bố theo frame rate
                        col5, col6 = st.columns(2)
                        with col5:
                            if (
                                "frameRate" in df.columns
                                and not df["frameRate"].isna().all()
                            ):
                                fps_counts = df["frameRate"].value_counts().head(10)
                                fig_fps = px.bar(
                                    x=fps_counts.index,
                                    y=fps_counts.values,
                                    title="Top 10 frame rate phổ biến",
                                    labels={"x": "Frame rate", "y": "Số lượng"},
                                )
                                st.plotly_chart(fig_fps, use_container_width=True)
                            else:
                                st.warning("Không có thông tin về frame rate")

                        # 6. Phân bố theo domain
                        with col6:
                            if "dmn" in df.columns and not df["dmn"].isna().all():
                                dmn_counts = df["dmn"].value_counts().head(10)
                                fig_dmn = px.bar(
                                    x=dmn_counts.index,
                                    y=dmn_counts.values,
                                    title="Top 10 domain phổ biến",
                                    labels={"x": "Domain", "y": "Số lượng"},
                                )
                                st.plotly_chart(fig_dmn, use_container_width=True)
                            else:
                                st.warning("Không có thông tin về domain")

                        # Hiển thị bảng dữ liệu
                        st.subheader("Danh sách bản ghi")
                        st.dataframe(df, use_container_width=True)

                    else:
                        st.warning("Không có dữ liệu trong khoảng thời gian đã chọn")

                # Xóa file tạm thời
                os.unlink(temp_key_path)

            except Exception as e:
                st.error(f"Lỗi kết nối: {str(e)}")
        else:
            st.warning("Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc")
    else:
        st.warning("Vui lòng chọn khoảng thời gian")

# Tab 2: Chi tiết Video
with tab2:

    # Input fileId và nút tìm kiếm
    col1, col2 = st.columns(2)
    with col1:
        file_id = st.text_input("Nhập File ID")
    with col2:
        search_button = st.button("Tìm kiếm")

    if search_button and file_id:
        try:
            # Đọc thông tin kết nối từ .env
            SSH_HOST = os.getenv("SSH_HOST")
            SSH_USER = os.getenv("SSH_USER")
            SSH_KEY = os.getenv("SSH_KEY")
            DB_NAME = "vieted_hls"
            COLLECTION_NAME = "files"

            # Tạo file tạm thời chứa SSH key
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_key:
                temp_key.write(SSH_KEY)
                temp_key_path = temp_key.name

            # Tạo SSH tunnel
            with SSHTunnelForwarder(
                (SSH_HOST, 22),
                ssh_username=SSH_USER,
                ssh_pkey=temp_key_path,
                remote_bind_address=("127.0.0.1", 27017),
            ) as tunnel:
                # Kết nối MongoDB
                client = pymongo.MongoClient(
                    f"mongodb://127.0.0.1:{tunnel.local_bind_port}/{DB_NAME}"
                )

                # Chọn database và collection
                db = client[DB_NAME]
                collection = db[COLLECTION_NAME]

                # Tìm video theo fileID
                video = collection.find_one({"fileID": file_id})

                if video:
                    # Xử lý dữ liệu video
                    video_data = process_video_data(video)

                    # Tạo layout 3 cột với tỷ lệ 2:1:1
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        # Hiển thị video player
                        display_video_player(video_data)

                    with col2:
                        st.subheader("Thông tin cơ bản")
                        st.write("**File ID:**", video_data.get("fileID", "N/A"))
                        st.write("**Tên file:**", video_data.get("fileName", "N/A"))
                        st.write("**Định dạng:**", video_data.get("extension", "N/A"))
                        st.write(
                            "**Trạng thái:**",
                            "Thành công" if video_data.get("status") == 1 else "Lỗi",
                        )
                        st.write("**DRM:**", "Có" if video_data.get("drm") else "Không")
                        st.write("**Domain:**", video_data.get("dmn", "N/A"))
                        st.write(
                            "**Response Status:**",
                            video_data.get("responseStatus", "N/A"),
                        )

                        # Thông tin link với nút copy
                        if video_data.get("hlsUrl"):
                            st.markdown(
                                f'<a href="{video_data["hlsUrl"]}">Link HLS</a>',
                                unsafe_allow_html=True,
                            )

                        if video_data.get("link_mp4"):
                            st.markdown(
                                f'<a href="{video_data["link_mp4"]}">Link MP4</a>',
                                unsafe_allow_html=True,
                            )

                    with col3:
                        st.subheader("Thông tin kỹ thuật")
                        st.write(
                            "**Kích thước:**",
                            f"{float(video_data.get('size', 0))/1024/1024:.2f} MB",
                        )
                        st.write(
                            "**Thời lượng:**",
                            f"{float(video_data.get('duration', 0))/60:.2f} phút",
                        )
                        st.write(
                            "**Bitrate:**",
                            f"{int(video_data.get('bitRate', 0))/1024:.2f} kbps",
                        )
                        st.write(
                            "**Độ phân giải:**",
                            f"{video_data.get('width', 0)}x{video_data.get('height', 0)}",
                        )
                        st.write("**Codec:**", video_data.get("codeName", "N/A"))
                        st.write("**FPS:**", video_data.get("frameRate", "N/A"))
                        st.write("**Ngày tạo:**", video_data.get("created_at", "N/A"))
                        st.write(
                            "**Ngày cập nhật:**", video_data.get("updated_at", "N/A")
                        )
                else:
                    st.warning("Không tìm thấy video với File ID này")

            # Xóa file tạm thời
            os.unlink(temp_key_path)

        except Exception as e:
            st.error(f"Lỗi kết nối: {str(e)}")
