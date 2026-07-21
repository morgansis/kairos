"""Monthly theater-style report helpers."""

from __future__ import annotations

import re
import html
import json
import urllib.parse
from pathlib import Path
from datetime import datetime

try:
    from ..utils.sys_helpers import format_display_path, format_size
except ImportError:  # pragma: no cover - direct script execution fallback
    from utils.sys_helpers import format_display_path, format_size

def generate_html_report(output_root_dir, month_key, media_records):
    if not media_records:
        return

    html_path = Path(output_root_dir) / f"{month_key}_media_report.html"
    generated_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    month_title = f"{month_key} 媒體處理報告"
    if re.fullmatch(r"\d{4}_\d{2}", str(month_key)):
        month_title = f"{month_key[:4]}年{month_key[5:7]}月的照片與影片"

    cards_html = []
    for rec in media_records:
        rel_path = rec['rel_path']
        display_rel_path = format_display_path(rel_path)
        # 關鍵修復：針對帶有空格或特殊字元的檔名進行 URL '%20' 轉碼，防止瀏覽器讀取本地檔案失敗
        rel_path_encoded = urllib.parse.quote(rel_path.replace('\\', '/'))

        fname = rec['name']
        escaped_fname = html.escape(fname, quote=True)
        fsize = format_size(rec['size'])
        category = rec['category']
        group_key = rec.get('group_key', Path(fname).stem)
        group_order = rec.get('group_order', 0)

        display_label = "IMAGE" if category == "standard" else category.upper()
        if category == "candidate": display_label = "備選"

        badge_style = "background: #7D8C94; color: white;"
        if category == "raw": badge_style = "background: #A88B87; color: white;"
        elif category == "video": badge_style = "background: #66747A; color: white;"
        elif category == "candidate": badge_style = "background: #E67E22; color: white;"

        error_div = '<div class="error-msg">檔案已刪除</div>'
        error_script = "this.closest('.media-card').classList.add('broken');"

        if category in ("standard", "candidate"):
            img_tag = f'<img data-src="{rel_path_encoded}" class="lazy-image" alt="{escaped_fname}" onerror="{error_script}">{error_div}'
        else:
            if category == "video":
                detector = f'<video src="{rel_path_encoded}" style="display:none;" onerror="{error_script}"></video>'
                img_tag = f'<div class="video-placeholder">影片檔案<br><small>{escaped_fname}</small><br><span style="font-size:11px; color:#3498DB;">[點擊播放]</span></div>{detector}{error_div}'
            elif category == "raw":
                img_tag = f'<div class="raw-placeholder">RAW 原檔<br><small>{escaped_fname}</small></div>{error_div}'
            else:
                img_tag = f'<div class="raw-placeholder">{escaped_fname}</div>{error_div}'

        # 新增：將地理位置整合進月份卡片中
        loc_name = rec.get('loc_name', '-')
        map_url = rec.get('map_url', '-')
        geo_html = ""
        if loc_name != "-" or map_url != "-":
            loc_display = html.escape(loc_name, quote=True) if loc_name != "-" else "未知位置"
            map_link_html = f'<a href="{map_url}" target="_blank" class="geo-map-btn" onclick="event.stopPropagation();" title="View on Google Maps">MAP</a>' if map_url != "-" else ""
            geo_html = f'<div class="geo-bar"><span class="geo-text" title="{loc_display}">{loc_display}</span>{map_link_html}</div>'

        # data-filepath 嚴格保留未轉碼之原始相對路徑，供 Windows/macOS 終端機刪除語法使用
        linked_raw_json = html.escape(json.dumps(rec.get("linked_raw_paths", []), ensure_ascii=False), quote=True)
        bundle_id = html.escape(str(rec.get("bundle_id", "")), quote=True)
        card = f"""
        <div class="media-card" data-category="{category}" data-name="{html.escape(fname.lower(), quote=True)}" data-group="{html.escape(group_key.lower(), quote=True)}" data-group-order="{group_order}" data-size="{rec['size']}" data-url="{rel_path_encoded}" data-filepath="{html.escape(str(Path(output_root_dir) / rel_path), quote=True)}" data-display-name="{escaped_fname}" data-bundle-id="{bundle_id}" data-linked-raw="{linked_raw_json}">
            <div class="img-container" onclick="openLightbox(this)" style="cursor: pointer;" title="點擊開啟全螢幕極限滿版瀏覽 / 影片串流">
                {img_tag}
            </div>
            <div class="info">
                <div class="filename" title="{escaped_fname}">{escaped_fname}</div>
                {geo_html}
                <div class="details">
                    <span class="badge" style="{badge_style}">{display_label}</span>
                    <span class="size">{fsize}</span>
                </div>
                <button class="card-del-btn" onclick="toggleCardDelete(this); event.stopPropagation();" title="標記/取消標記為待刪除">標記刪除</button>
            </div>
        </div>
        """
        cards_html.append(card)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{month_title}</title>
    <style>
        :root {{ --bg: #F4F6F7; --card-bg: #FFFFFF; --text: #4A4F54; --border: #E0E4E6; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ background: var(--card-bg); padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        h1 {{ margin: 0 0 10px 0; font-size: 24px; color: #2C3E50; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; }}
        .generated-time {{ color: #95A5A6; font-size: 13px; font-weight: normal; }}
        .controls {{ display: flex; flex-wrap: wrap; gap: 15px; align-items: center; margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border); }}
        .btn-group {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        button {{ background: #7D8C94; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; transition: 0.2s; font-weight: bold; }}
        button:hover, button.active {{ background: #4A4F54; }}
        select {{ padding: 8px; border-radius: 5px; border: 1px solid var(--border); outline: none; font-size: 14px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }}
        .media-card {{ background: var(--card-bg); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); box-shadow: 0 2px 4px rgba(0,0,0,0.03); transition: transform 0.2s, border-color 0.2s; display: flex; flex-direction: column; }}
        .media-card:hover {{ transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
        .media-card.marked-delete {{ border: 2px solid #e74c3c; background: #FFF8F8; opacity: 0.75; }}
        .img-container {{ width: 100%; height: 180px; background: #EAECEE; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }}
        .lazy-image {{ width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.3s ease; }}
        .lazy-image.loaded {{ opacity: 1; }}
        .video-placeholder, .raw-placeholder {{ text-align: center; color: #7F8C8D; font-weight: bold; padding: 10px; }}
        .info {{ padding: 12px; display: flex; flex-direction: column; flex-grow: 1; justify-content: space-between; gap: 8px; }}
        .filename {{ font-size: 13px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .geo-bar {{ display: flex; justify-content: space-between; align-items: center; font-size: 11px; background: #F8F9F9; padding: 4px 6px; border-radius: 4px; border: 1px solid var(--border); gap: 4px; }}
        .geo-text {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #5D6D7E; flex-grow: 1; }}
        .geo-map-btn {{ color: #2980B9; text-decoration: none; font-weight: bold; flex-shrink: 0; background: #EAF2F8; padding: 2px 6px; border-radius: 3px; transition: 0.2s; }}
        .geo-map-btn:hover {{ background: #D4E6F1; text-decoration: underline; }}
        .details {{ display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #7F8C8D; }}
        .badge {{ padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; }}
        .card-del-btn {{ background: #EAECEE; color: #7F8C8D; font-size: 11px; padding: 5px; width: 100%; border-radius: 4px; margin-top: 5px; }}
        .media-card.marked-delete .card-del-btn {{ background: #e74c3c; color: white; }}
        .error-msg {{ display: none; padding: 20px; font-size: 12px; color: #999; text-align: center; }}
        .media-card.broken .lazy-image, .media-card.broken .video-placeholder, .media-card.broken .raw-placeholder {{ display: none !important; }}
        .media-card.broken .error-msg {{ display: block !important; }}
        .delete-bar {{ background: #FFF3CD; border: 1px solid #FFEEBA; color: #856404; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: none; align-items: center; gap: 20px; font-weight: bold; }}
        .delete-btns {{ display: flex; flex-direction: row; gap: 8px; flex-wrap: wrap; }}
        .btn-copy {{ background: #27AE60; color: white; width: 250px; text-align: left; }}
        .btn-copy:hover {{ background: #1E8449; }}
        .lightbox {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100vw; height: 100vh; background-color: #000000; align-items: center; justify-content: center; overflow: hidden; }}
        .lightbox-content {{ width: 100vw; height: 100vh; max-width: 100vw; max-height: 100vh; object-fit: contain; }}
        .lightbox-top-bar {{ position: absolute; top: 0; left: 0; width: 100%; padding: 20px 30px; background: linear-gradient(to bottom, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%); display: flex; justify-content: space-between; align-items: center; z-index: 1002; box-sizing: border-box; pointer-events: none; }}
        .lightbox-top-bar * {{ pointer-events: auto; }}
        .lightbox-caption {{ color: #F4F6F7; font-size: 16px; text-shadow: 0 1px 3px rgba(0,0,0,0.8); }}
        .lightbox-close {{ color: #FFF; font-size: 42px; font-weight: bold; cursor: pointer; transition: 0.2s; user-select: none; line-height: 1; }}
        .lightbox-close:hover {{ color: #e74c3c; }}
        .nav-arrow {{ position: absolute; top: 50%; transform: translateY(-50%); color: rgba(255,255,255,0.7); font-size: 60px; font-weight: bold; cursor: pointer; padding: 20px 15px; user-select: none; transition: 0.2s; z-index: 1002; }}
        .nav-arrow:hover {{ color: #FFF; background-color: rgba(255,255,255,0.15); border-radius: 8px; }}
        .prev-arrow {{ left: 15px; }}
        .next-arrow {{ right: 15px; }}
        .lightbox-bottom-bar {{ position: absolute; bottom: 0; left: 0; width: 100%; padding: 25px 30px; background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%); display: flex; justify-content: center; align-items: center; z-index: 1002; box-sizing: border-box; pointer-events: none; }}
        .lightbox-bottom-bar * {{ pointer-events: auto; }}
        .lightbox-del-btn {{ background: rgba(125,140,148,0.9); color: white; padding: 12px 30px; border-radius: 30px; font-size: 15px; font-weight: bold; cursor: pointer; border: 2px solid white; transition: 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }}
        .lightbox-del-btn:hover {{ background: #4A4F54; transform: scale(1.05); }}
        .lightbox-del-btn.marked {{ background: #e74c3c; border-color: #ffd700; }}
        .lightbox-msg {{ color: #FFF; font-size: 18px; text-align: center; padding: 40px; background: #2C3E50; border-radius: 8px; z-index: 1001; }}
    </style>
</head>
<body>
    <header>
        <h1>
            <span>{month_title} <span class="generated-time">(Generated : {generated_ts})</span></span>
            <span style="font-size: 15px; font-weight: normal; color:#7F8C8D;">總共收錄: <strong>{len(media_records)}</strong> 個檔案</span>
        </h1>
        <div class="delete-bar" id="deleteBar">
            <span id="deleteCountText">已標記 0 個待刪除檔案</span>
            <div class="delete-btns">
                <button class="btn-copy" onclick="copyDeleteCommands('win')" title="直接複製 del /f /q 指令，於 CMD 貼上即可刪除">Windows CMD 刪除指令</button>
                <button class="btn-copy" style="background:#5B4B8A;" onclick="copyDeleteCommands('powershell')" title="直接複製 Remove-Item 指令，於 Windows PowerShell 貼上即可刪除">Windows PowerShell 刪除指令</button>
                <button class="btn-copy" style="background:#2980B9;" onclick="copyDeleteCommands('mac')" title="直接複製 rm -f 指令，於 macOS 終端機貼上即可刪除">複製 macOS/Linux 刪除指令</button>
            </div>
        </div>
        <div class="controls">
            <span>過濾篩選:</span>
            <div class="btn-group">
                <button class="filter-btn active" onclick="filterSelection('all')">全部</button>
                <button class="filter-btn" onclick="filterSelection('standard')">照片</button>
                <button class="filter-btn" onclick="filterSelection('video')">影片</button>
            </div>
            <span style="margin-left:auto;">排序方式:</span>
            <select id="sortSelect" onchange="sortGrid()">
                <option value="name-asc">檔名 (A -> Z)</option>
                <option value="name-desc">檔名 (Z -> A)</option>
                <option value="size-desc">大小 (大 -> 小)</option>
                <option value="size-asc">大小 (小 -> 大)</option>
            </select>
        </div>
    </header>

    <div class="grid" id="mediaGrid">
        {"".join(cards_html)}
    </div>

    <!-- 100vw/100vh 究極滿版懸浮燈箱 -->
    <div id="lightbox" class="lightbox" onclick="if(event.target === this) closeLightbox();">
        <div class="lightbox-top-bar">
            <div id="lightbox-caption" class="lightbox-caption"></div>
            <span class="lightbox-close" onclick="closeLightbox()" title="關閉燈箱 (Esc)">&times;</span>
        </div>
        <a class="nav-arrow prev-arrow" onclick="changeSlide(-1, event)" title="上一張 (方向鍵左)">&#10094;</a>
        <a class="nav-arrow next-arrow" onclick="changeSlide(1, event)" title="下一張 (方向鍵右 / 空白鍵)">&#10095;</a>
        <img id="lightbox-img" class="lightbox-content" src="" alt="" style="display:none;">
        <video id="lightbox-video" class="lightbox-content" controls style="display:none; background:#000;" onclick="event.stopPropagation();"></video>
        <div id="lightbox-msg" class="lightbox-msg" style="display:none;"></div>
        <div class="lightbox-bottom-bar">
            <button id="lightbox-del-btn" class="lightbox-del-btn" onclick="toggleLightboxDelete(event)" title="快速鍵: Delete / Backspace">標記為刪除</button>
        </div>
    </div>

    <script>
        let currentVisibleCards = [];
        let currentIndex = 0;

        document.addEventListener("DOMContentLoaded", function() {{
            initLazyLoad();
            sortGrid();
        }});

        function initLazyLoad() {{
            let lazyImages = [].slice.call(document.querySelectorAll("img.lazy-image"));
            if ("IntersectionObserver" in window) {{
                let lazyImageObserver = new IntersectionObserver(function(entries, observer) {{
                    entries.forEach(function(entry) {{
                        if (entry.isIntersecting) {{
                            let lazyImage = entry.target;
                            lazyImage.src = lazyImage.dataset.src;
                            lazyImage.onload = () => lazyImage.classList.add("loaded");
                            lazyImageObserver.unobserve(lazyImage);
                        }}
                    }});
                }});
                lazyImages.forEach(function(lazyImage) {{ lazyImageObserver.observe(lazyImage); }});
            }} else {{
                lazyImages.forEach(function(lazyImage) {{
                    lazyImage.src = lazyImage.dataset.src;
                    lazyImage.classList.add("loaded");
                }});
            }}
        }}

        function filterSelection(category) {{
            let cards = document.getElementsByClassName("media-card");
            let btns = document.getElementsByClassName("filter-btn");
            for (let btn of btns) {{ btn.classList.remove("active"); }}
            event.target.classList.add("active");

            for (let card of cards) {{
                if (category === "all" || card.getAttribute("data-category") === category) {{
                    card.style.display = "flex";
                }} else {{
                    card.style.display = "none";
                }}
            }}
            updateVisibleCardsList();
        }}

        function sortGrid() {{
            let grid = document.getElementById("mediaGrid");
            let cards = Array.from(grid.getElementsByClassName("media-card"));
            let sortValue = document.getElementById("sortSelect").value;

            cards.sort(function(a, b) {{
                if (sortValue === "name-asc") {{ let groupCompare = a.dataset.group.localeCompare(b.dataset.group); return groupCompare || (parseInt(a.dataset.groupOrder) - parseInt(b.dataset.groupOrder)) || a.dataset.name.localeCompare(b.dataset.name); }}
                if (sortValue === "name-desc") return b.dataset.name.localeCompare(a.dataset.name);
                if (sortValue === "size-desc") return parseInt(b.dataset.size) - parseInt(a.dataset.size);
                if (sortValue === "size-asc") return parseInt(a.dataset.size) - parseInt(b.dataset.size);
            }});

            for (let card of cards) {{ grid.appendChild(card); }}
            updateVisibleCardsList();
        }}

        function updateVisibleCardsList() {{
            let grid = document.getElementById("mediaGrid");
            currentVisibleCards = Array.from(grid.getElementsByClassName("media-card")).filter(c => c.style.display !== "none");
        }}

        // --- 標記刪除與一鍵剪貼簿功能 ---
        function toggleCardDelete(btn) {{
            let card = btn.closest(".media-card");
            card.classList.toggle("marked-delete");
            btn.innerText = card.classList.contains("marked-delete") ? "已標記刪除" : "標記刪除";
            updateDeleteUI();
        }}

        function toggleLightboxDelete(e) {{
            if (e) e.stopPropagation();
            let card = currentVisibleCards[currentIndex];
            if (!card) return;
            card.classList.toggle("marked-delete");
            let btn = card.querySelector(".card-del-btn");
            if (btn) btn.innerText = card.classList.contains("marked-delete") ? "已標記刪除" : "標記刪除";
            updateDeleteUI();
            updateLightboxDeleteBtn();
        }}

        function updateLightboxDeleteBtn() {{
            let lbDelBtn = document.getElementById("lightbox-del-btn");
            let card = currentVisibleCards[currentIndex];
            if (card && card.classList.contains("marked-delete")) {{
                lbDelBtn.classList.add("marked");
                lbDelBtn.innerText = "已標記為刪除 (點此或按 Delete 取消)";
            }} else {{
                lbDelBtn.classList.remove("marked");
                lbDelBtn.innerText = "標記為刪除 (點此或按 Delete)";
            }}
        }}

        function updateDeleteUI() {{
            let markedCards = document.querySelectorAll(".media-card.marked-delete");
            let bar = document.getElementById("deleteBar");
            let txt = document.getElementById("deleteCountText");
            if (markedCards.length > 0) {{
                bar.style.display = "flex";
                txt.innerText = `已標記 ${{markedCards.length}} 個待刪除檔案`;
            }} else {{
                bar.style.display = "none";
            }}
        }}

        function quotePosixShell(path) {{
            return "'" + path.replace(/'/g, "'\\"'\\"'") + "'";
        }}

        function parseLinkedRaw(card) {{
            const raw = card.dataset.linkedRaw || "[]";
            try {{
                const parsed = JSON.parse(raw);
                return Array.isArray(parsed) ? parsed : [];
            }} catch (e) {{
                return [];
            }}
        }}

        function collectDeleteTargets(markedCards) {{
            const targets = new Set();
            let hasLinkedRaw = false;
            markedCards.forEach(card => {{
                const primaryPath = card.dataset.filepath || card.dataset.url;
                if (primaryPath) targets.add(primaryPath);
                const linkedRawPaths = parseLinkedRaw(card);
                if (linkedRawPaths.length > 0) {{
                    hasLinkedRaw = true;
                    linkedRawPaths.forEach(path => {{
                        if (path) targets.add(path);
                    }});
                }}
            }});
            return {{ targets: Array.from(targets), hasLinkedRaw }};
        }}

        function copyDeleteCommands(type) {{
            let markedCards = document.querySelectorAll(".media-card.marked-delete");
            if (markedCards.length === 0) return;
            const {{ targets, hasLinkedRaw }} = collectDeleteTargets(markedCards);
            if (targets.length === 0) return;

            if (hasLinkedRaw) {{
                const shouldContinue = confirm("系統偵測到關聯的 RAW 原始檔，將連同標記的 JPG 一併加入刪除指令。確定要繼續嗎？");
                if (!shouldContinue) return;
            }}

            let content = "";
            if (type === 'win') {{
                targets.forEach(path => {{
                    let relPath = String(path).replace(/\\//g, '\\\\');
                    content += `del /f /q "${{relPath}}"\\r\\n`;
                }});
            }} else if (type === 'powershell') {{
                targets.forEach(path => {{
                    let relPath = String(path).replace(/\\//g, '\\\\');
                    let literalPath = relPath.replace(/'/g, "''");
                    content += `Remove-Item -LiteralPath '${{literalPath}}' -Force\\r\\n`;
                }});
            }} else {{
                targets.forEach(path => {{
                    let relPath = String(path);
                    content += `rm -f ${{quotePosixShell(relPath)}}\\n`;
                }});
            }}

            navigator.clipboard.writeText(content).then(() => {{
                alert(`已成功複製 ${{targets.length}} 筆刪除指令到剪貼簿！\\n\\n請在輸出根目錄開啟對應的 CMD、Windows PowerShell 或 macOS/Linux 終端機，再貼上執行。`);
            }}).catch(err => {{
                alert("無法自動寫入剪貼簿，請改為點擊右方下載按鈕保存腳本。");
            }});
        }}

        function openLightbox(element) {{
            document.body.style.overflow = 'hidden';
            updateVisibleCardsList();
            let card = element.closest(".media-card");
            currentIndex = currentVisibleCards.indexOf(card);
            showSlide(currentIndex);
            document.getElementById("lightbox").style.display = "flex";
        }}

        function closeLightbox() {{
            document.body.style.overflow = '';
            let lbVid = document.getElementById("lightbox-video");
            lbVid.pause();
            lbVid.src = "";
            document.getElementById("lightbox").style.display = "none";
        }}

        function changeSlide(step, e) {{
            if (e) e.stopPropagation();
            currentIndex += step;
            if (currentIndex >= currentVisibleCards.length) currentIndex = 0;
            if (currentIndex < 0) currentIndex = currentVisibleCards.length - 1;
            showSlide(currentIndex);
        }}

        function showSlide(index) {{
            let card = currentVisibleCards[index];
            if (!card) return;
            let imgUrl = card.dataset.url;
            let name = card.dataset.displayName;
            let category = card.dataset.category;
            let displayCategory = (category === 'standard') ? 'IMAGE' : category.toUpperCase();

            let lbImg = document.getElementById("lightbox-img");
            let lbVid = document.getElementById("lightbox-video");
            let lbMsg = document.getElementById("lightbox-msg");
            let lbCaption = document.getElementById("lightbox-caption");

            lbVid.pause();
            lbCaption.innerHTML = `<strong>${{name}}</strong> <span style="background:#A88B87; color:white; padding:2px 8px; border-radius:10px; font-size:12px; margin-left:8px;">${{displayCategory}}</span> <span style="color:#BDC3C7; font-size:14px; margin-left:12px;">第 ${{index + 1}} / ${{currentVisibleCards.length}} 張</span>`;

            if (category === "video") {{
                lbImg.style.display = "none";
                lbMsg.style.display = "none";
                lbVid.style.display = "block";
                lbVid.src = imgUrl;
                lbVid.play().catch(() => console.log("瀏覽器阻擋自動播放，需手動點擊"));
            }} else if (category === "raw") {{
                lbImg.style.display = "none";
                lbVid.style.display = "none";
                lbMsg.style.display = "block";
                lbMsg.innerHTML = `RAW 原檔不支援瀏覽器線上大圖預覽<br><br><a href="${{imgUrl}}" target="_blank" style="color: #F39C12; text-decoration: underline; font-weight:bold;">點此下載 / 新分頁開啟原始檔 (${{name}})</a>`;
            }} else {{
                lbVid.style.display = "none";
                lbMsg.style.display = "none";
                lbImg.style.display = "block";
                lbImg.src = imgUrl;
            }}
            updateLightboxDeleteBtn();
        }}

        document.addEventListener("keydown", function(e) {{
            let lb = document.getElementById("lightbox");
            if (lb.style.display === "flex") {{
                if (e.key === "ArrowRight" || e.key === " ") {{
                    e.preventDefault();
                    changeSlide(1);
                }} else if (e.key === "ArrowLeft") {{
                    e.preventDefault();
                    changeSlide(-1);
                }} else if (e.key === "Escape") {{
                    closeLightbox();
                }} else if (e.key === "Delete" || e.key === "Backspace") {{
                    e.preventDefault();
                    toggleLightboxDelete();
                }}
            }}
        }});
    </script>
</body>
</html>"""

    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        pass

__all__ = ["generate_html_report"]
