"""Root index report helpers."""

from __future__ import annotations

import html
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from ..config.constants import PLACEHOLDER
    from ..metadata.geo_engine import get_stats_banner_html
    from ..utils.sys_helpers import format_display_path
except ImportError:  # pragma: no cover - direct script execution fallback
    from config.constants import PLACEHOLDER
    from metadata.geo_engine import get_stats_banner_html
    from utils.sys_helpers import format_display_path

def destination_extension_counts(dest_path):
    excluded = {'_index.html', '_manifest_audit.csv', '_manifest_skiplist.txt', '_manifest_filetype.html'}
    return Counter(p.suffix.lower() or '[無副檔名]' for p in dest_path.rglob('*') if p.is_file() and p.name not in excluded and not p.name.startswith('_process_log') and not p.name.endswith('_media_report.html'))

def generate_file_type_summary(output_root_dir, audit_manifest):
    """產生獨立的副檔名統計頁；目的地數量以本次最終實體檔為準。"""
    source = Counter(row[4].lower() or '[無副檔名]' for row in audit_manifest)
    copied = Counter(row[4].lower() or '[no_ext]' for row in audit_manifest if row[6] == 'PASS')
    skipped = Counter(row[4].lower() or '[no_ext]' for row in audit_manifest if row[6] == 'SKIP')
    failed = Counter(row[4].lower() or '[no_ext]' for row in audit_manifest if row[6] == 'FAIL')
    destination = destination_extension_counts(Path(output_root_dir))
    extensions = sorted(set(source) | set(destination))
    rows = ''.join(
        f"<tr><td>{html.escape(ext)}</td><td>{source[ext]:,}</td><td>{copied[ext]:,}</td><td>{skipped[ext]:,}</td><td>{failed[ext]:,}</td><td>{destination[ext]:,}</td></tr>"
        for ext in extensions
    )
    generated_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = f'''<!doctype html><html lang="zh-TW"><meta charset="utf-8"><title>檔案類型統計</title>
    <style>body{{font-family:Segoe UI,sans-serif;margin:24px;color:#2c3e50}}table{{border-collapse:collapse;width:100%;max-width:900px}}th,td{{padding:9px 12px;border:1px solid #dfe6e9;text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{background:#eef2f3}}</style>
    <h1>檔案類型統計 <span style="color:#95A5A6;font-size:13px;font-weight:normal;">(Generated : {generated_ts})</span></h1><p>來源掃描數包含本次掃描範圍內所有副檔名；目的地實際數不含程式產生的報表與日誌。</p>
    <table><tr><th>Ext</th><th>Scanned</th><th>PASS</th><th>SKIP</th><th>FAIL</th><th>Dest Count</th></tr>{rows}</table></html>'''
    with open(Path(output_root_dir) / '_manifest_filetype.html', 'w', encoding='utf-8') as f:
        f.write(content)

def generate_manifest_html(output_root_dir, audit_manifest):
    if not audit_manifest:
        return
    import json
    html_path = Path(output_root_dir) / "_index.html"
    generated_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    has_geo_column = any(len(row) > 9 for row in audit_manifest)
    geo_filter_btn_html = '<button onclick="setFilter(\'status\', \'GEO\', this)">🌏 GEO</button>' if has_geo_column else ''
    geo_header_html = '<th>地圖</th>' if has_geo_column else ''

    clean_data = []
    for row in audit_manifest:
        normalized = [
            str(row[0]),
            # Normalize non-path placeholders to "-"
            format_display_path(row[1]) if (row[1] and row[1] != PLACEHOLDER) else PLACEHOLDER,
            format_display_path(row[2]) if (row[2] and row[2] != PLACEHOLDER) else PLACEHOLDER,
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6]),
            str(row[7]),
            str(row[8])
        ]
        if has_geo_column:
            normalized.append(str(row[9]) if len(row) > 9 else PLACEHOLDER)
        clean_data.append(normalized)

    # 2. 將 Python List 轉為壓縮版 JSON 字串 (去除多餘空白，體積縮小 80%)
    json_data_str = json.dumps(clean_data, ensure_ascii=False, separators=(',', ':'))

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>照片影片處理總報表</title>
    <style>
        :root {{ --bg: #F4F6F7; --card-bg: #FFFFFF; --text: #4A4F54; --border: #E0E4E6; --main: #7D8C94; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ background: var(--card-bg); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; }}
        h1 {{ margin: 0 0 15px 0; font-size: 22px; color: #2C3E50; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
        .generated-time {{ color: #95A5A6; font-size: 13px; font-weight: normal; }}
        .filter-bar {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; border-top: 1px solid var(--border); padding-top: 15px; }}
        .btn-group {{ display: flex; gap: 6px; flex-wrap: wrap; }}
        button {{ background: var(--main); color: white; border: none; padding: 6px 14px; border-radius: 5px; cursor: pointer; transition: 0.2s; font-size: 13px; font-weight: bold; }}
        button:hover, button.active {{ background: #2C3E50; }}
        button:disabled {{ background: #BDC3C7; cursor: not-allowed; }}
        input[type="text"] {{ padding: 8px 12px; border-radius: 5px; border: 1px solid var(--border); outline: none; font-size: 14px; width: 280px; }}

        /* 分頁控制器 */
        .pagination-bar {{ display: flex; justify-content: space-between; align-items: center; background: var(--card-bg); padding: 12px 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid var(--border); flex-wrap: wrap; gap: 10px; }}
        .page-info {{ font-weight: bold; color: #2C3E50; font-size: 14px; }}
        select {{ padding: 6px 10px; border-radius: 5px; border: 1px solid var(--border); font-size: 13px; outline: none; }}

        .table-container {{ background: var(--card-bg); border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow-x: auto; border: 1px solid var(--border); min-height: 500px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; white-space: nowrap; }}
        th {{ background: #EAECEE; color: #2C3E50; padding: 12px 15px; font-weight: bold; border-bottom: 2px solid var(--border); position: sticky; top: 0; z-index: 10; }}
        td {{ padding: 10px 15px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:hover {{ background-color: #F8F9F9; }}
        tr.has-plugin-warn {{ background-color: #FFFDF0; }}
        tr.has-plugin-warn:hover {{ background-color: #FFF9D6; }}

        .font-bold {{ font-weight: bold; color: #2C3E50; }}
        .path-cell {{ max-width: 250px; overflow: hidden; text-overflow: ellipsis; color: #7F8C8D; }}
        .reason-cell {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}
        .plugin-cell {{ max-width: 250px; overflow: hidden; text-overflow: ellipsis; color: #D68910; font-weight: 500; }}
        .cam-badge {{ background: #EAEDED; color: #5D6D7E; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
        .status-badge {{ padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        .status-success {{ background: #D4EFDF; color: #196F3D; }}
        .status-skip {{ background: #FCF3CF; color: #B7950B; }}
        .status-fail {{ background: #FADBD8; color: #943126; }}
    </style>
</head>
<body>
    <header>
        <h1>
            <span>📋 照片影片處理總報表 <span class="generated-time">(Generated : {generated_ts})</span></span>
            <span style="font-size: 14px; color: #7F8C8D; font-weight: normal;">總收錄: <strong id="totalCount" style="color:#2C3E50;">0</strong> 筆資料</span>
        </h1>
        {get_stats_banner_html()}
        <div class="filter-bar">
            <button onclick="window.open('_manifest_filetype.html','fileTypeSummary','width=980,height=720')">檔案類型統計</button>
            <span>🔍 搜尋過濾:</span>
            <input type="text" id="searchInput" oninput="debounceFilter()" placeholder="關鍵字 (檔名、相機、插件訊息)...">

            <span style="margin-left: 10px;">狀態篩選:</span>
            <div class="btn-group" id="statusBtns">
                <button class="active" onclick="setFilter('status', 'all', this)">全部</button>
                {geo_filter_btn_html}
                <button onclick="setFilter('status', 'PASS', this)">✅ PASS</button>
                <button onclick="setFilter('status', 'SKIP', this)">⏭️ SKIP</button>
                <button onclick="setFilter('status', 'FAIL', this)">❌ FAIL</button>
            </div>

            <span style="margin-left: 10px;">類別:</span>
            <div class="btn-group" id="catBtns">
                <button class="active" onclick="setFilter('cat', 'all', this)">全部</button>
                <button onclick="setFilter('cat', 'standard', this)">照片</button>
                <button onclick="setFilter('cat', 'video', this)">影片</button>
                <button onclick="setFilter('cat', 'raw', this)">RAW</button>
            </div>
        </div>
    </header>

    <!-- 分頁控制列 -->
    <div class="pagination-bar">
        <div class="btn-group">
            <button id="btnFirst" onclick="changePage(1)">⏪ 第一頁</button>
            <button id="btnPrev" onclick="changePage(currentPage - 1)">◀ 上一頁</button>
            <button id="btnNext" onclick="changePage(currentPage + 1)">下一頁 ▶</button>
            <button id="btnLast" onclick="changePage(totalPages)">最末頁 ⏩</button>
        </div>
        <div class="page-info">
            第 <span id="pageSpan" style="color:#E74C3C; font-size:16px;">1</span> / <span id="totalPageSpan">1</span> 頁
            (目前顯示：<span id="showingRangeSpan">0 - 0</span> 筆)
        </div>
        <div>
            每頁顯示:
            <select id="pageSizeSelect" onchange="changePageSize()">
                <option value="100">100 筆</option>
                <option value="250" selected>250 筆</option>
                <option value="500">500 筆</option>
                <option value="1000">1000 筆</option>
            </select>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>檔案名稱</th>
                    <th>來源完整路徑</th>
                    <th>輸出目標路徑</th>
                    <th>相機型號</th>
                    <th>副檔名</th>
                    {geo_header_html}
                    <th>處理類別</th>
                    <th>最終狀態</th>
                    <th>詳細說明/略過原因</th>
                    <th>插件訊息</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <!-- 資料會透過 JS 記憶體分頁極速渲染 -->
            </tbody>
        </table>
    </div>

    <script>
        // 1. 載入原始 JSON 大數據陣列
        const RAW_DATA = {json_data_str};
        const HAS_GEO_COL = {"true" if has_geo_column else "false"};

        let filteredData = RAW_DATA;
        let currentPage = 1;
        let pageSize = 250;
        let totalPages = 1;

        let filterState = {{ status: 'all', cat: 'all', keyword: '' }};
        let filterTimeout = null;

        document.addEventListener("DOMContentLoaded", function() {{
            document.getElementById("totalCount").innerText = RAW_DATA.length.toLocaleString();
            applyFilters();
        }});

        function setFilter(type, value, btn) {{
            filterState[type] = value;
            let container = (type === 'status') ? document.getElementById("statusBtns") : document.getElementById("catBtns");
            let btns = container.getElementsByTagName("button");
            for (let b of btns) b.classList.remove("active");
            btn.classList.add("active");
            applyFilters();
        }}

        // 使用 Debounce 避免連續敲打鍵盤時重複運算
        function debounceFilter() {{
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(() => {{
                filterState.keyword = document.getElementById("searchInput").value.trim().toLowerCase();
                applyFilters();
            }}, 150);
        }}

        // 記憶體極速過濾核心 (26 萬筆僅耗時幾毫秒)
        function applyFilters() {{
            let kw = filterState.keyword;
            filteredData = RAW_DATA.filter(row => {{
                if (filterState.status === 'GEO') {{
                    if (!(HAS_GEO_COL && String(row[9] || "-") !== "-")) return false;
                }} else if (filterState.status !== 'all' && row[6] !== filterState.status) {{
                    return false;
                }}
                if (filterState.cat !== 'all' && row[5] !== filterState.cat) return false;
                if (kw !== "") {{
                    let searchStr = (row[0] + " " + row[3] + " " + row[8] + " " + (HAS_GEO_COL ? (row[9] || "") : "")).toLowerCase();
                    if (searchStr.indexOf(kw) === -1) return false;
                }}
                return true;
            }});

            currentPage = 1;
            updatePagination();
            renderTable();
        }}

        function changePageSize() {{
            pageSize = parseInt(document.getElementById("pageSizeSelect").value);
            currentPage = 1;
            updatePagination();
            renderTable();
        }}

        function changePage(targetPage) {{
            if (targetPage < 1 || targetPage > totalPages || targetPage === currentPage) return;
            currentPage = targetPage;
            updatePagination();
            renderTable();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function updatePagination() {{
            let totalRecords = filteredData.length;
            totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
            if (currentPage > totalPages) currentPage = totalPages;

            document.getElementById("pageSpan").innerText = currentPage.toLocaleString();
            document.getElementById("totalPageSpan").innerText = totalPages.toLocaleString();

            let startIdx = (totalRecords === 0) ? 0 : (currentPage - 1) * pageSize + 1;
            let endIdx = Math.min(currentPage * pageSize, totalRecords);
            document.getElementById("showingRangeSpan").innerText = `${{startIdx.toLocaleString()}} - ${{endIdx.toLocaleString()}}`;

            document.getElementById("btnFirst").disabled = (currentPage === 1);
            document.getElementById("btnPrev").disabled = (currentPage === 1);
            document.getElementById("btnNext").disabled = (currentPage === totalPages || totalRecords === 0);
            document.getElementById("btnLast").disabled = (currentPage === totalPages || totalRecords === 0);
        }}

        // 僅渲染當前頁面的 250 筆 HTML 節點，徹底解決記憶體與卡死問題
        function renderTable() {{
            let tbody = document.getElementById("tableBody");
            if (filteredData.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="${{HAS_GEO_COL ? 10 : 9}}" style="text-align:center; padding:30px; color:#999;">找不到符合條件的資料</td></tr>`;
                return;
            }}

            let startIdx = (currentPage - 1) * pageSize;
            let endIdx = Math.min(startIdx + pageSize, filteredData.length);
            let pageData = filteredData.slice(startIdx, endIdx);

            let htmlRows = pageData.map(row => {{
                let fname = escapeHtml(row[0]);
                let srcP = escapeHtml(row[1]);
                let dstP = escapeHtml(row[2]);
                let cam = escapeHtml(row[3]);
                let ext = escapeHtml(row[4]);
                let cat = escapeHtml(row[5]);
                let status = escapeHtml(row[6]);
                let reason = escapeHtml(row[7]);
                let plugin = escapeHtml(row[8]);
                let geoMap = HAS_GEO_COL ? String(row[9] || "-") : "-";

                let dstCellHtml = dstP;
                if ((status === "PASS" || reason.indexOf("IDENTICAL") !== -1) && dstP !== "-" && dstP.indexOf("ALL_MEDIA") === -1) {{
                    let match = dstP.match(/(\\d{{4}}_\\d{{2}})/);
                    if (match) {{
                        let monthReportUrl = `./${{match[1]}}_media_report.html`;
                        dstCellHtml = `<a href="${{monthReportUrl}}" target="_blank" style="color:#2980B9; text-decoration:underline; font-weight:bold;">${{dstP}}</a>`;
                    }}
                }}

                let statusClass = "status-success";
                if (status === "SKIP") statusClass = "status-skip";
                else if (status === "FAIL") statusClass = "status-fail";

                let geoCellHtml = (HAS_GEO_COL && geoMap !== "-")
                    ? `<a href="${{escapeHtml(geoMap)}}" target="_blank" title="View on Google Maps">&#127757;</a>`
                    : "-";

                let rowClass = (plugin !== "-") ? "has-plugin-warn" : "";

                return `<tr class="${{rowClass}}">
                    <td class="font-bold">${{fname}}</td>
                    <td class="path-cell" title="${{srcP}}">${{srcP}}</td>
                    <td class="path-cell" title="${{dstP}}">${{dstCellHtml}}</td>
                    <td><span class="cam-badge">${{cam}}</span></td>
                    <td>${{ext}}</td>
                    ${{HAS_GEO_COL ? `<td>${{geoCellHtml}}</td>` : ``}}
                    <td>${{cat}}</td>
                    <td><span class="status-badge ${{statusClass}}">${{status}}</span></td>
                    <td class="reason-cell" title="${{reason}}">${{reason}}</td>
                    <td class="plugin-cell" title="${{plugin}}">${{plugin}}</td>
                </tr>`;
            }});

            tbody.innerHTML = htmlRows.join('');
        }}

        function escapeHtml(str) {{
            return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }}
    </script>
</body>
</html>"""
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass

__all__ = [
    "destination_extension_counts",
    "generate_file_type_summary",
    "generate_manifest_html",
]
