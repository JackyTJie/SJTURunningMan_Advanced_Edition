import math
import statistics
from collections import Counter

from utils.auxiliary_util import haversine_distance


LOW_RISK_MAX = 39
MEDIUM_RISK_MAX = 69
HIGH_RISK_MIN = 70


def analyze_running_payload(payload):
    """
    Analyze a generated running payload and return a conservative risk report.

    The analyzer is intentionally read-only: it never mutates the payload and is
    designed for rule testing / anti-cheat diagnostics before upload.
    """
    points = _extract_points(payload)
    findings = []

    if len(points) < 2:
        return _build_result(
            90,
            {"point_count": len(points), "distance_m": 0.0, "duration_sec": 0.0},
            [_finding("结构异常", 90, "有效轨迹点少于 2 个，无法形成可验证轨迹。")],
            forced_level="high",
        )

    segments = _build_segments(points)
    positive_segments = [seg for seg in segments if seg["dt"] > 0]
    total_distance = sum(seg["distance"] for seg in positive_segments)
    duration_sec = max(0.0, (points[-1]["time"] - points[0]["time"]) / 1000.0)
    moving_speeds = [seg["speed"] for seg in positive_segments if seg["speed"] >= 0.5]

    non_increasing_count = sum(1 for seg in segments if seg["dt"] <= 0)
    severe_jump_count = sum(
        1
        for seg in positive_segments
        if seg["speed"] >= 12.0 and seg["distance"] >= 30.0
    )

    if non_increasing_count:
        findings.append(_finding(
            "结构异常",
            45,
            f"发现 {non_increasing_count} 处时间戳非递增，轨迹时序无效。",
        ))

    if severe_jump_count:
        findings.append(_finding(
            "结构异常",
            35,
            f"发现 {severe_jump_count} 处疑似 GPS 跳点或超高速移动。",
        ))

    findings.extend(_score_time_regularity(positive_segments))
    findings.extend(_score_speed_stability(moving_speeds, positive_segments))
    findings.extend(_score_linear_interpolation(positive_segments))
    findings.extend(_score_gps_noise(points, positive_segments))
    findings.extend(_score_route_repetition(points))
    findings.extend(_score_status_consistency(points))

    score = min(100, int(round(sum(item["score"] for item in findings))))
    forced_level = "high" if non_increasing_count or severe_jump_count else None

    stats = {
        "point_count": len(points),
        "track_count": _track_count(payload),
        "distance_m": round(total_distance, 2),
        "duration_sec": round(duration_sec, 1),
        "avg_speed_mps": round(total_distance / duration_sec, 3) if duration_sec > 0 else 0.0,
        "moving_speed_cv": round(_coefficient_of_variation(moving_speeds), 4)
        if moving_speeds
        else None,
        "non_increasing_timestamps": non_increasing_count,
        "severe_jump_count": severe_jump_count,
    }

    return _build_result(score, stats, findings, forced_level=forced_level)


def _extract_points(payload):
    points = []
    if not isinstance(payload, list):
        return points

    for run in payload:
        if not isinstance(run, dict):
            continue
        for track_index, track in enumerate(run.get("tracks", []) or []):
            if not isinstance(track, dict):
                continue
            status = track.get("status", "unknown")
            tstate = track.get("tstate", "")
            for point in track.get("points", []) or []:
                lat_lng = point.get("latLng", {}) if isinstance(point, dict) else {}
                try:
                    lat = float(lat_lng["latitude"])
                    lon = float(lat_lng["longitude"])
                    locatetime = int(point["locatetime"])
                except (KeyError, TypeError, ValueError):
                    continue

                points.append({
                    "lat": lat,
                    "lon": lon,
                    "time": locatetime,
                    "status": status,
                    "tstate": tstate,
                    "track_index": track_index,
                    "location": point.get("location", ""),
                })
    return points


def _build_segments(points):
    segments = []
    for index in range(len(points) - 1):
        first = points[index]
        second = points[index + 1]
        dt = (second["time"] - first["time"]) / 1000.0
        distance = haversine_distance(first["lat"], first["lon"], second["lat"], second["lon"])
        speed = distance / dt if dt > 0 else math.inf
        bearing = _bearing_degrees(first["lat"], first["lon"], second["lat"], second["lon"])
        segments.append({
            "dt": dt,
            "distance": distance,
            "speed": speed,
            "bearing": bearing,
            "start_status": first["status"],
            "end_status": second["status"],
            "track_index": first["track_index"],
        })
    return segments


def _score_time_regularity(segments):
    if len(segments) < 12:
        return []

    dts = [seg["dt"] for seg in segments if 0 < seg["dt"] < 30]
    if len(dts) < 12:
        return []

    cv = _coefficient_of_variation(dts)
    rounded_counts = Counter(round(dt, 1) for dt in dts)
    dominant_ratio = rounded_counts.most_common(1)[0][1] / len(dts)

    score = 0
    detail = ""
    if cv < 0.015 and dominant_ratio >= 0.9:
        score = 18
        detail = f"采样间隔几乎固定，变异系数 {cv:.3f}，主间隔占比 {dominant_ratio:.0%}。"
    elif cv < 0.035 and dominant_ratio >= 0.8:
        score = 13
        detail = f"采样间隔高度规律，变异系数 {cv:.3f}，主间隔占比 {dominant_ratio:.0%}。"
    elif dominant_ratio >= 0.9:
        score = 8
        detail = f"大量轨迹点落在同一采样间隔，主间隔占比 {dominant_ratio:.0%}。"

    return [_finding("时间采样规律性", score, detail)] if score else []


def _score_speed_stability(moving_speeds, segments):
    if len(moving_speeds) < 12:
        return []

    speed_cv = _coefficient_of_variation(moving_speeds)
    score = 0
    detail = ""
    if speed_cv < 0.025:
        score = 18
        detail = f"移动速度过度稳定，速度变异系数仅 {speed_cv:.3f}。"
    elif speed_cv < 0.05:
        score = 13
        detail = f"移动速度波动偏低，速度变异系数 {speed_cv:.3f}。"
    elif speed_cv < 0.08:
        score = 8
        detail = f"移动速度波动较小，速度变异系数 {speed_cv:.3f}。"

    accelerations = []
    for prev, current in zip(segments, segments[1:]):
        dt = current["dt"]
        if prev["dt"] > 0 and dt > 0 and math.isfinite(prev["speed"]) and math.isfinite(current["speed"]):
            accelerations.append((current["speed"] - prev["speed"]) / dt)

    if len(accelerations) >= 12:
        accel_std = statistics.pstdev(accelerations)
        if accel_std < 0.025:
            score += 4
            detail = (detail + " " if detail else "") + f"加速度变化也异常平滑，标准差 {accel_std:.3f}。"

    score = min(22, score)
    return [_finding("速度过度稳定", score, detail)] if score else []


def _score_linear_interpolation(segments):
    moving = [seg for seg in segments if seg["dt"] > 0 and seg["distance"] >= 1.0]
    if len(moving) < 18:
        return []

    equal_distance_flags = []
    straight_flags = []
    combined_flags = []

    for prev, current in zip(moving, moving[1:]):
        max_dist = max(prev["distance"], current["distance"])
        distance_delta_ratio = abs(prev["distance"] - current["distance"]) / max_dist if max_dist > 0 else 0
        angle_delta = _angle_difference(prev["bearing"], current["bearing"])
        equal_distance = distance_delta_ratio <= 0.035
        straight = angle_delta <= 2.0
        equal_distance_flags.append(equal_distance)
        straight_flags.append(straight)
        combined_flags.append(equal_distance and straight)

    equal_ratio = _true_ratio(equal_distance_flags)
    straight_ratio = _true_ratio(straight_flags)
    longest_combined_run = _longest_true_run(combined_flags)

    score = 0
    detail = ""
    if equal_ratio >= 0.8 and straight_ratio >= 0.75 and longest_combined_run >= 12:
        score = 18
        detail = (
            f"连续点呈明显等距直线插值特征，等距占比 {equal_ratio:.0%}，"
            f"小转角占比 {straight_ratio:.0%}，最长连续 {longest_combined_run} 段。"
        )
    elif equal_ratio >= 0.68 and straight_ratio >= 0.62 and longest_combined_run >= 8:
        score = 12
        detail = (
            f"存在较长等距直线片段，等距占比 {equal_ratio:.0%}，"
            f"小转角占比 {straight_ratio:.0%}。"
        )
    elif longest_combined_run >= 16:
        score = 7
        detail = f"发现较长的等距直线连续片段，最长 {longest_combined_run} 段。"

    return [_finding("线性插值痕迹", score, detail)] if score else []


def _score_gps_noise(points, segments):
    if len(points) < 20:
        return []

    score = 0
    details = []

    precision_ratio = _uniform_location_precision_ratio(points)
    if precision_ratio >= 0.95:
        score += 4
        details.append(f"坐标小数精度高度一致，占比 {precision_ratio:.0%}。")

    local_deviations = _local_cross_track_deviations(points)
    if len(local_deviations) >= 12:
        median_deviation = statistics.median(local_deviations)
        if median_deviation < 0.2:
            score += 7
            details.append(f"局部横向抖动极低，中位偏移 {median_deviation:.2f}m。")
        elif median_deviation < 0.45:
            score += 4
            details.append(f"局部横向抖动偏低，中位偏移 {median_deviation:.2f}m。")

    distances = [seg["distance"] for seg in segments if seg["dt"] > 0 and seg["distance"] >= 1.0]
    if len(distances) >= 12:
        dist_cv = _coefficient_of_variation(distances)
        if dist_cv < 0.04:
            score += 5
            details.append(f"相邻点距离分布过于集中，变异系数 {dist_cv:.3f}。")

    score = min(14, score)
    return [_finding("GPS 噪声/精度异常", score, " ".join(details))] if score else []


def _score_route_repetition(points):
    if len(points) < 20:
        return []

    quantized = [_quantize_point(point, decimals=5) for point in points]
    duplicate_count = len(quantized) - len(set(quantized))
    duplicate_ratio = duplicate_count / len(quantized)

    window_size = 6
    windows = [
        tuple(quantized[index:index + window_size])
        for index in range(0, max(0, len(quantized) - window_size + 1))
    ]
    repeated_windows = sum(count - 1 for count in Counter(windows).values() if count > 1)
    repeated_window_ratio = repeated_windows / len(windows) if windows else 0

    reverse_repeats = 0
    if windows:
        window_set = set(windows)
        reverse_repeats = sum(1 for window in window_set if tuple(reversed(window)) in window_set)
    reverse_ratio = reverse_repeats / len(set(windows)) if windows else 0

    score = 0
    details = []
    if duplicate_ratio >= 0.25:
        score += 6
        details.append(f"路线坐标重复率较高，约 {duplicate_ratio:.0%}。")
    elif duplicate_ratio >= 0.12:
        score += 3
        details.append(f"存在一定比例重复坐标，约 {duplicate_ratio:.0%}。")

    if repeated_window_ratio >= 0.18:
        score += 7
        details.append(f"重复片段占比 {repeated_window_ratio:.0%}。")
    elif repeated_window_ratio >= 0.08:
        score += 4
        details.append(f"检测到重复路线片段，占比 {repeated_window_ratio:.0%}。")

    if reverse_ratio >= 0.18:
        score += 5
        details.append(f"正反向片段高度一致，占比 {reverse_ratio:.0%}。")

    score = min(16, score)
    return [_finding("路线重复与机械往返", score, " ".join(details))] if score else []


def _score_status_consistency(points):
    if len(points) < 2:
        return []

    by_track = {}
    for point in points:
        by_track.setdefault(point["track_index"], []).append(point)

    stop_tracks = 0
    moving_stop_tracks = 0
    invalid_moving_tracks = 0
    low_speed_pair_count = 0
    moving_pair_count = 0

    for track_points in by_track.values():
        if len(track_points) < 2:
            continue

        status = track_points[0]["status"]
        distance = 0.0
        for first, second in zip(track_points, track_points[1:]):
            dt = (second["time"] - first["time"]) / 1000.0
            dist = haversine_distance(first["lat"], first["lon"], second["lat"], second["lon"])
            distance += dist
            if dt > 0:
                speed = dist / dt
                if speed < 0.5:
                    low_speed_pair_count += 1
                if speed >= 0.5:
                    moving_pair_count += 1

        duration = max(0.0, (track_points[-1]["time"] - track_points[0]["time"]) / 1000.0)
        avg_speed = distance / duration if duration > 0 else 0.0

        if status == "stop":
            stop_tracks += 1
            if avg_speed > 0.8 and distance > 8:
                moving_stop_tracks += 1
        elif status == "invalid" and avg_speed > 1.2 and distance > 20:
            invalid_moving_tracks += 1

    score = 0
    details = []
    if moving_stop_tracks:
        score += 7
        details.append(f"{moving_stop_tracks} 个停止段仍保持明显位移。")
    if stop_tracks and low_speed_pair_count == 0 and moving_pair_count >= 10:
        score += 4
        details.append("轨迹声明存在停止段，但点级速度中未出现低速停顿。")
    if invalid_moving_tracks:
        score += 4
        details.append(f"{invalid_moving_tracks} 个无效段仍呈连续正常移动。")

    score = min(12, score)
    return [_finding("停顿/状态一致性", score, " ".join(details))] if score else []


def _build_result(score, stats, findings, forced_level=None):
    findings = sorted(
        [item for item in findings if item.get("score", 0) > 0],
        key=lambda item: item["score"],
        reverse=True,
    )
    level = forced_level or _risk_level(score)
    summary = _summary_text(score, level, findings)
    return {
        "score": score,
        "level": level,
        "level_label": _level_label(level),
        "stats": stats,
        "findings": findings,
        "summary": summary,
    }


def _summary_text(score, level, findings):
    if findings:
        top_reasons = "；".join(item["detail"] for item in findings[:3] if item.get("detail"))
    else:
        top_reasons = "未发现明显机械轨迹特征。"
    return f"轨迹风险指数 {score}/100（{_level_label(level)}）：{top_reasons}"


def _finding(name, score, detail):
    return {"name": name, "score": int(score), "detail": detail}


def _risk_level(score):
    if score <= LOW_RISK_MAX:
        return "low"
    if score <= MEDIUM_RISK_MAX:
        return "medium"
    return "high"


def _level_label(level):
    labels = {"low": "低风险", "medium": "中风险", "high": "高风险"}
    return labels.get(level, "未知")


def _track_count(payload):
    if not isinstance(payload, list):
        return 0
    return sum(len(run.get("tracks", []) or []) for run in payload if isinstance(run, dict))


def _coefficient_of_variation(values):
    usable = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
    if len(usable) < 2:
        return 0.0
    mean_value = statistics.mean(usable)
    if abs(mean_value) < 1e-9:
        return 0.0
    return statistics.pstdev(usable) / abs(mean_value)


def _bearing_degrees(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    lambda1 = math.radians(lon1)
    lambda2 = math.radians(lon2)
    y = math.sin(lambda2 - lambda1) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(lambda2 - lambda1)
    )
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _angle_difference(first, second):
    diff = abs(first - second) % 360.0
    return min(diff, 360.0 - diff)


def _true_ratio(flags):
    return sum(1 for flag in flags if flag) / len(flags) if flags else 0.0


def _longest_true_run(flags):
    longest = 0
    current = 0
    for flag in flags:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _uniform_location_precision_ratio(points):
    precision_pairs = []
    for point in points:
        location = point.get("location") or ""
        if "," not in location:
            continue
        lon_text, lat_text = location.split(",", 1)
        if "." not in lon_text or "." not in lat_text:
            continue
        precision_pairs.append((len(lon_text.split(".", 1)[1]), len(lat_text.split(".", 1)[1])))

    if not precision_pairs:
        return 0.0

    most_common_count = Counter(precision_pairs).most_common(1)[0][1]
    return most_common_count / len(precision_pairs)


def _local_cross_track_deviations(points):
    deviations = []
    for previous, current, following in zip(points, points[1:], points[2:]):
        base_distance = haversine_distance(previous["lat"], previous["lon"], following["lat"], following["lon"])
        if base_distance < 2.0:
            continue

        a = haversine_distance(previous["lat"], previous["lon"], current["lat"], current["lon"])
        b = haversine_distance(current["lat"], current["lon"], following["lat"], following["lon"])
        c = base_distance
        semiperimeter = (a + b + c) / 2.0
        area_term = semiperimeter * (semiperimeter - a) * (semiperimeter - b) * (semiperimeter - c)
        if area_term <= 0:
            deviations.append(0.0)
            continue
        area = math.sqrt(area_term)
        deviations.append((2.0 * area) / c)
    return deviations


def _quantize_point(point, decimals=5):
    return (round(point["lat"], decimals), round(point["lon"], decimals))
