"""Main workflow orchestration helpers."""

from __future__ import annotations

import os
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

def threaded_process_images(selected_folders, dest_dir, organize_by_time, normalize_name, enable_geo_lookup, copy_video, copy_raw, overwrite, performance_mode, q, stop_event):
    dest_path = Path(dest_dir)
    report_lines = []
    audit_manifest = []
    CAPTURE_META_CACHE.clear()

    # 歸零全域戰情數據
    GEO_PERF_STATS['queries'] = 0
    GEO_PERF_STATS['cache_hits'] = 0
    GEO_PERF_STATS['new_lookups'] = 0
    GEO_PERF_STATS['copied'] = 0
    GEO_PERF_STATS['skipped'] = 0
    GEO_PERF_STATS['total_time'] = 0.0

    if performance_mode:
        q.put(('log', "[PERF] Performance mode enabled: less log / fast scan / GEO fail summary"))

    if not organize_by_time and len(selected_folders) != 1:
        q.put(('msgbox', ("設定錯誤", "未啟用依年月整理時，來源與目的資料夾為 1:1，無法處理多個來源資料夾。"), 'warning', None))
        q.put(('reset', None))
        return

    # 🚀 執行前：搜尋原本來源目錄 (及父目錄) 與目的目錄，聯集載入歷史 _manifest_geo.json
    if enable_geo_lookup:
        load_and_merge_geo_caches(selected_folders, dest_dir, log_callback=lambda m: q.put(('log', m)))

    if enable_geo_lookup and not RG_AVAILABLE:
        q.put(('log', "[GEO] FAIL: reverse_geocoder unavailable; only EXIF GPS and map URL will be used."))

    if enable_geo_lookup and RG_AVAILABLE:
        q.put(('status', "⏳ Loading global offline geo database (first load may take a few seconds)..."))
        try:
            _ = rg.search((24.989, 121.313))
            q.put(('log', "✅ Global offline geo database loaded and index warmed up."))
        except Exception as e:
            q.put(('log', f"⚠️ [GEO] ERROR: database preload failed: {e}"))
            enable_geo_lookup = False

    files = []
    valid_extensions = set(STANDARD_EXTENSIONS)
    if copy_raw: valid_extensions.update(RAW_EXTENSIONS)
    if copy_video: valid_extensions.update(VIDEO_EXTENSIONS)

    # 走訪所有被選目錄
    for folder in selected_folders:
        if stop_event.is_set(): break
        for dirpath, dirnames, filenames in os.walk(folder):
            if stop_event.is_set(): break

            # 關鍵修復：針對被 EXCLUDE_DIR_KEYWORDS 排除的目錄，強制攔截並輸出日誌理由
            removed_dirs = [d for d in dirnames if any(keyword in d.lower() for keyword in EXCLUDE_DIR_KEYWORDS)]
            for d in removed_dirs:
                skip_path = format_display_path(os.path.join(dirpath, d))
                skip_msg = f"[SKIP_DIR] {skip_path} | REASON: ignored directory ({d})"
                report_lines.append(skip_msg + "\n")
                if not performance_mode:
                    q.put(('log', skip_msg))
            dirnames[:] = [d for d in dirnames if d not in removed_dirs]

            display_path = format_display_path(dirpath)
            display_path = display_path if len(display_path) <= 65 else "..." + display_path[-62:]
            q.put(('status', f"🔍 Scanning directory: {display_path}"))

            # 走訪所有檔案
            for filename in filenames:
                # 精確過濾：只有符合 Kairos 系統特徵的檔案才執行「靜默忽略」
                if is_kairos_self_file(filename):
                    continue

                ext = os.path.splitext(filename)[1].lower()
                full_src_p = os.path.join(dirpath, filename)
                full_src_win_p = format_display_path(full_src_p)

                if ext in IGNORED_EXTENSIONS:
                    # 如果您希望連一般被忽略的檔案都不刷屏，這裡的 append 也可以保留現狀或改為 debug 級別
                    report_lines.append(f"[SKIP_FILE] {full_src_win_p} | REASON: ignored extension ({ext})\n")
                    audit_manifest.append([filename, full_src_win_p, "-", "-", ext, "ignored", "SKIP", f"ignored extension ({ext})", "-"])
                    continue

                if ext in valid_extensions:
                    files.append(Path(dirpath) / filename)
                else:
                    report_lines.append(f"[SKIP] {full_src_win_p} | REASON: unsupported extension ({ext})\n")
                    audit_manifest.append([filename, full_src_win_p, "-", "-", ext, "ignored", "SKIP", f"unsupported extension ({ext})", "-"])

    if stop_event.is_set():
        q.put(('status', "🛑 Processing interrupted"))
        q.put(('reset', None))
        return

    total_files = len(files)
    if total_files == 0:
        q.put(('msgbox', ("提示", "所選目錄中找不到符合的媒體檔。"), 'info', None))
        q.put(('reset', None))
        return

    success_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()
    processed_size_bytes = 0
    q.put(('status', f"First Pass | safe collection and dup-skip: 0 / {total_files} (0.0%)"))

    monthly_media_map = {}

    for i, file_path in enumerate(files):
        if stop_event.is_set(): break

        full_win_path = format_display_path(file_path)

        try: file_size = os.path.getsize(file_path)
        except OSError: file_size = 0

        # 用於記錄該檔案處理過程中的外掛異常訊息
        captured_warnings = []
        camera_model = "-"
        loc_name, map_url = "-", "-"

        try:
            ext = file_path.suffix.lower()
            stem = file_path.stem

            # 讀取相機型號同時攔截插件訊息
            if not performance_mode:
                with PluginWarningCapturer() as capturer:
                    camera_model = get_camera_model(file_path)
                captured_warnings.extend(capturer.get_messages())

            timestamp_base, _ = timestamp_parts(stem)
            clean_stem = timestamp_base or stem

            if timestamp_base:
                year, month = timestamp_base[:4], timestamp_base[5:7]
                target_name = f"{clean_stem}{ext}"
            else:
                if organize_by_time or normalize_name:
                    # 使用攔截器包覆 get_media_date
                    if performance_mode:
                        media_date = get_media_date(file_path)
                    else:
                        with PluginWarningCapturer() as capturer:
                            media_date = get_media_date(file_path)
                        captured_warnings.extend(capturer.get_messages())

                    year = media_date.strftime('%Y')
                    month = media_date.strftime('%m')
                    target_name = f"{media_date.strftime('%Y-%m-%d %H.%M.%S')}{ext}" if normalize_name else f"{clean_stem}{ext}"
                else:
                    year, month = None, None
                    target_name = f"{clean_stem}{ext}"

            if organize_by_time:
                month_key = f"{year}_{month}"
                target_dir = dest_path / month_key
                category = "standard"

                if ext in RAW_EXTENSIONS:
                    target_dir /= "raw"
                    category = "raw"
                elif ext in VIDEO_EXTENSIONS:
                    category = "video"
            else:
                month_key = "ALL_MEDIA"
                target_dir = dest_path / file_path.parent.relative_to(Path(selected_folders[0]).parent)
                category = "standard"
                if ext in RAW_EXTENSIONS: category = "raw"
                elif ext in VIDEO_EXTENSIONS: category = "video"

            # 去除重複的警告字句並以分號連接成單一行
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else PLACEHOLDER

            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / target_name

            effective_category = category
            is_duplicate_skip = False
            skip_reason = None

            # 取得正規化後的最終目標主檔名 (例如 "2017-10-15 17.38.59")
            target_stem = target_file.stem
            
            # 在進行衝突命名與 unique_path 前，先全面檢查該群組所有序號後綴是否存在實體相同檔案
            identical_match = find_identical_in_target(file_path, target_dir, target_stem, ext)

            if identical_match:
                is_duplicate_skip = True
                skip_reason = f"[Target existed] {identical_match.name}"
                target_file = identical_match

            elif target_file.exists():
                overwrite_photo_mode = overwrite and category == "standard" and ext in STANDARD_EXTENSIONS
                decision = compare_and_decide(file_path, target_file)

                if decision == "IDENTICAL":
                    is_duplicate_skip = True
                    skip_reason = f"[Target existed] {target_file.name}"

                elif overwrite_photo_mode and decision == "SAME_MS":
                    src_mtime = os.path.getmtime(file_path)
                    tgt_mtime = os.path.getmtime(target_file)
                    if src_mtime > tgt_mtime:
                        archived = candidate_path_for(target_dir, target_file.stem, ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(archived)
                        target_file.rename(archived)
                        if not performance_mode:
                            q.put(('log', f"[OVERWRITE] SAME_MS: archived previous to candidate -> {archived.name}"))
                    else:
                        target_file = candidate_path_for(target_dir, target_file.stem, ext)
                        effective_category = "candidate" if category == "standard" else category

                elif overwrite_photo_mode and decision == "BURST":
                    src_meta = get_capture_meta(file_path)
                    tgt_meta = get_capture_meta(target_file)
                    base_stem = timestamp_base or target_file.stem
                    src_ms = src_meta.get('subsec_ms')
                    tgt_ms = tgt_meta.get('subsec_ms')

                    if tgt_ms and target_file.stem == base_stem:
                        existing_burst_path = unique_path(target_dir, f"{base_stem}-{tgt_ms}", ext)
                        invalidate_capture_meta(target_file)
                        invalidate_capture_meta(existing_burst_path)
                        target_file.rename(existing_burst_path)
                        if not performance_mode:
                            q.put(('log', f"[OVERWRITE] BURST: renamed existing -> {existing_burst_path.name}"))

                    if src_ms:
                        target_file = unique_path(target_dir, f"{base_stem}-{src_ms}", ext)
                    else:
                        target_file = unique_indexed_path(target_dir, base_stem, ext, start=1)

                elif overwrite_photo_mode and decision == "REPLACE":
                    archived = candidate_path_for(target_dir, target_file.stem, ext)
                    invalidate_capture_meta(target_file)
                    invalidate_capture_meta(archived)
                    target_file.rename(archived)
                    if not performance_mode:
                        q.put(('log', f"[OVERWRITE] REPLACE: archived previous to candidate -> {archived.name}"))

                elif overwrite_photo_mode and decision == "KEEP":
                    target_file = candidate_path_for(target_dir, target_file.stem, ext)
                    effective_category = "candidate" if category == "standard" else category

                else:
                    target_file = unique_path(target_dir, target_file.stem, ext)

            if target_file.parent.name == 'candidate' and effective_category == "standard":
                effective_category = "candidate"

            if is_duplicate_skip:
                skipped_count += 1
                processed_size_bytes += file_size
                report_lines.append(f"[SKIP: IDENTICAL] {full_win_path} | REASON: {skip_reason}\n")
                audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, effective_category, "SKIP", skip_reason, plugin_msg_str])
                q.put(('metrics', processed_size_bytes))  # 直接丟總大小！
                q.put(('progress', (i + 1) / total_files))
                continue

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # 嚴格守則：只有在 Target 目錄執行複製與寫入，絕對不觸碰、不污染來源資料夾
                    shutil.copy2(file_path, target_file)
                    invalidate_capture_meta(target_file)

                    log_path = target_dir / "_process_log.txt"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    with open(log_path, 'a', encoding='utf-8') as log_f:
                        log_f.write(f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}\n")

                    if organize_by_time:
                        rel_p = target_file.relative_to(dest_path).as_posix()
                        if month_key not in monthly_media_map:
                            monthly_media_map[month_key] = []

                        if effective_category != "raw":
                            monthly_media_map[month_key].append({
                                'name': target_file.name,
                                'rel_path': rel_p,
                                'size': file_size,
                                'category': effective_category,
                                'loc_name': loc_name,
                                'map_url': map_url
                            })

                    audit_manifest.append([file_path.name, str(file_path), str(target_file), camera_model, ext, effective_category, "PASS", "COPY_OK", plugin_msg_str])
                    if not performance_mode:
                        q.put(('log', f"[{timestamp}] Processed: {file_path.name} -> {target_file.name}"))

                    # 若該檔案有外掛異常訊息，同步輸出在 UI 日誌提示
                    if not performance_mode and plugin_msg_str != "-":
                        q.put(('log', f"⚠️ [PLUGIN] {file_path.name}: {plugin_msg_str}"))

                    success_count += 1
                    break
                except (PermissionError, OSError) as e:
                    if attempt < max_retries - 1: time.sleep(0.5)
                    else: raise e

        except Exception as e:
            failed_count += 1
            plugin_msg_str = " ; ".join(dict.fromkeys(captured_warnings)) if captured_warnings else "-"
            report_lines.append(f"[FAIL] {full_win_path} | REASON: processing exception ({str(e)})\n")
            audit_manifest.append([file_path.name, str(file_path), PLACEHOLDER, camera_model, ext, PLACEHOLDER, "FAIL", f"ERROR: processing exception: {str(e)}", plugin_msg_str])
            q.put(('error_log', f"ERROR while processing {file_path.name}: {e}"))

        processed_size_bytes += file_size
        display_file_path = full_win_path if len(full_win_path) <= 65 else "..." + full_win_path[-62:]
        phase_elapsed = time.time() - start_time
        rate = (i + 1) / phase_elapsed if phase_elapsed > 0 else 0
        remaining = (total_files - i - 1) / rate if rate > 0 else 0
        q.put(('progress', (i + 1) / total_files))
        overall_remaining = remaining * 1.15  # 第二輪尚未取得實際群組數，先以保守係數估算。
        q.put(('status', f"First Pass | safe collection and duplicate-skip: {i + 1} / {total_files} ({(i + 1) / total_files:.1%}) | elapsed {format_time(phase_elapsed)} | phase remaining {format_time(remaining)} | overall ETA {format_time(overall_remaining)} | {display_file_path}"))
        q.put(('metrics', processed_size_bytes))  # 直接丟總大小！

    # Second Pass：同秒連拍衝突與候選整理
    if not stop_event.is_set() and organize_by_time and overwrite:
        month_dirs = [p for p in dest_path.iterdir() if p.is_dir() and re.fullmatch(r'\d{4}_\d{2}', p.name)]
        second_start = time.time()
        for index, month_dir in enumerate(month_dirs, start=1):
            elapsed = time.time() - second_start
            rate = (index - 1) / elapsed if elapsed > 0 and index > 1 else 0
            remaining = (len(month_dirs) - index + 1) / rate if rate else 0
            q.put(('status', f"Second Pass | organizing burst sets and alternates: {index} / {len(month_dirs)} ({index / max(len(month_dirs), 1):.1%}) | elapsed {format_time(elapsed)} | overall ETA {format_time(remaining)} | {month_dir.name}"))
            second_pass_month(month_dir, stop_event)
            q.put(('progress', index / max(len(month_dirs), 1)))
            q.put(('metrics', processed_size_bytes))

    generated_html_reports = []
    index_report_path = None
    geo_stats = {'pass': 0, 'fail': 0, 'skip': 0}
    geo_fail_by_abs_path = {}
    geo_map_by_abs_path = {}
    if not stop_event.is_set():
        # 進行最終產出路徑掃描與「批量空間矩陣解析」
        monthly_media_map, geo_stats, geo_fail_by_abs_path, geo_map_by_abs_path, geo_fail_reason_counter = collect_media_records(
            dest_path, organize_by_time, enable_geo_lookup, q, stop_event, start_time, processed_size_bytes, performance_mode
        )

        # 處理完畢後：將更新後的地理空間快取字典封存回目標輸出目錄
        if enable_geo_lookup:
            save_geo_cache_to_dest(dest_dir, log_callback=lambda m: q.put(('log', m)))

        # 在生成 HTML 報表前，統計最終完成的執行時間與處理張數
        GEO_PERF_STATS['total_time'] = time.time() - start_time
        GEO_PERF_STATS['copied'] = success_count
        GEO_PERF_STATS['skipped'] = skipped_count

        q.put(('status', "Generating HTML preview reports from final file state..."))
        for m_key, records in monthly_media_map.items():
            generate_html_report(dest_path, m_key, records)
            generated_html_reports.append((m_key, dest_path / f"{m_key}_media_report.html"))

    if audit_manifest:
        try:
            if enable_geo_lookup:
                q.put(('log', f"🧭 GEO stats | PASS: {geo_stats.get('pass', 0)} | FAIL: {geo_stats.get('fail', 0)} | SKIP: {geo_stats.get('skip', 0)}"))
                if performance_mode and geo_fail_reason_counter:
                    summary_parts = [f"{reason} x{count}" for reason, count in geo_fail_reason_counter.most_common(5)]
                    q.put(('log', f"[GEO] FAIL summary: {' | '.join(summary_parts)}"))
                for row in audit_manifest:
                    if len(row) < 10:
                        row.append(PLACEHOLDER)
                    target_path = row[2]
                    if target_path == PLACEHOLDER:
                        continue
                    geo_key = os.path.normcase(os.path.abspath(str(target_path)))
                    geo_reason = geo_fail_by_abs_path.get(geo_key)
                    if not geo_reason:
                        geo_url = geo_map_by_abs_path.get(geo_key)
                        if geo_url:
                            row[9] = geo_url
                        continue
                    geo_msg = f"[GEO] {geo_reason}"
                    row[8] = geo_msg if row[8] == PLACEHOLDER else f"{row[8]} ; {geo_msg}"
                    geo_url = geo_map_by_abs_path.get(geo_key)
                    if geo_url:
                        row[9] = geo_url

            manifest_path = dest_path / "_manifest_audit.csv"
            with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                # 新增「相機型號」,「插件訊息」欄位；地理解析啟用時加上「地圖」
                has_geo_column = any(len(row) > 9 for row in audit_manifest)
                header = ['檔案名稱', '來源完整路徑', '輸出目標路徑', '相機型號', '副檔名', '處理類別', '最終狀態', '詳細說明/略過原因', '插件訊息']
                if has_geo_column:
                    header.append('地圖')
                writer.writerow(header)
                writer.writerows([
                    [
                        row[0],
                        format_display_path(row[1]) if row[1] != PLACEHOLDER else PLACEHOLDER,
                        format_display_path(row[2]) if row[2] != PLACEHOLDER else PLACEHOLDER,
                        *(row[3:] if has_geo_column else row[3:9])
                    ]
                    for row in audit_manifest
                ])
            q.put(('log', f"📋 CSV report exported: {manifest_path.name}"))

            generate_file_type_summary(dest_path, audit_manifest)
            # 同步產出 HTML 總報表
            generate_manifest_html(dest_path, audit_manifest)
            index_report_path = dest_path / "_index.html"
            q.put(('log', f"🌐 HTML report exported: _index.html"))

        except Exception as e:
            q.put(('error_log', f"ERROR: failed to export CSV audit report: {e}"))

    report_msg_append = ""
    if report_lines:
        try:
            report_file_path = dest_path / "_manifest_skiplist.txt"
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(f"=== 媒體處理例外報告 (產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")
                f.write(f"TOTAL SKIP: {skipped_count} | TOTAL FAIL: {failed_count}\n")
                f.write("="*80 + "\n")
                f.writelines(report_lines)
            report_msg_append = f"\n\n📄 報表已輸出至output根目錄:\n_manifest_skiplist.txt\n_manifest_audit.csv\n_index.html"
        except Exception: pass

    if stop_event.is_set():
        msg = f"中斷前已處理數量統計\n\n✅ PASS: {success_count}\n⏭️ SKIP: {skipped_count}\n❌ FAIL: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("中斷", msg), 'warning', None, index_report_path))
    else:
        msg = f"本次處理檔案數量統計\n\n✅ PASS: {success_count}\n⏭️ SKIP: {skipped_count}\n❌ FAIL: {failed_count}{report_msg_append}"
        q.put(('msgbox', ("完成", msg), 'info', generated_html_reports, index_report_path))

    q.put(('reset', None))

__all__ = ["threaded_process_images"]
