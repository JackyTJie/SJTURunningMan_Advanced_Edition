import html
import json

from utils.auxiliary_util import haversine_distance


BAIDU_MAP_AK = "MYUXpppuOOvq99cP2AmDvplAW76VV8vr"
JUMP_THRESHOLD_METERS = 150.0
UPLOAD_LONGITUDE_OFFSET = -0.00651271494735 + 0.000094
UPLOAD_LATITUDE_OFFSET = -0.00560888976477 - 0.000700


def build_route_preview(payload, run_index=None, total_runs=None, status="待上传", risk_analysis=None):
    """Build a serializable preview object from the actual upload payload."""
    points = extract_payload_points(payload)
    if len(points) < 2:
        return {
            "available": False,
            "run_index": run_index,
            "total_runs": total_runs,
            "status": status,
            "points": points,
            "stats": {
                "point_count": len(points),
                "track_count": _track_count(payload),
                "distance_m": 0.0,
                "duration_sec": 0.0,
                "start_end_m": 0.0,
                "max_segment_m": 0.0,
                "jump_count": 0,
            },
            "jump_segments": [],
            "risk": _risk_summary(risk_analysis),
            "summary": "暂无可预览路线",
        }

    segments = []
    total_distance = 0.0
    max_segment = 0.0
    jump_segments = []

    for index, (first, second) in enumerate(zip(points, points[1:])):
        distance = haversine_distance(first["lat"], first["lng"], second["lat"], second["lng"])
        total_distance += distance
        max_segment = max(max_segment, distance)
        segment = {
            "from_index": index,
            "to_index": index + 1,
            "distance_m": round(distance, 2),
            "from": {"lng": first["lng"], "lat": first["lat"]},
            "to": {"lng": second["lng"], "lat": second["lat"]},
            "display_from": {"lng": first["display_lng"], "lat": first["display_lat"]},
            "display_to": {"lng": second["display_lng"], "lat": second["display_lat"]},
        }
        segments.append(segment)
        if distance > JUMP_THRESHOLD_METERS:
            jump_segments.append(segment)

    duration_sec = max(0.0, (points[-1]["time"] - points[0]["time"]) / 1000.0)
    start_end_m = haversine_distance(points[0]["lat"], points[0]["lng"], points[-1]["lat"], points[-1]["lng"])

    stats = {
        "point_count": len(points),
        "track_count": _track_count(payload),
        "distance_m": round(total_distance, 2),
        "duration_sec": round(duration_sec, 1),
        "start_end_m": round(start_end_m, 2),
        "max_segment_m": round(max_segment, 2),
        "jump_count": len(jump_segments),
    }
    risk = _risk_summary(risk_analysis)
    summary = format_preview_summary({
        "available": True,
        "run_index": run_index,
        "total_runs": total_runs,
        "status": status,
        "stats": stats,
        "risk": risk,
    })

    return {
        "available": True,
        "run_index": run_index,
        "total_runs": total_runs,
        "status": status,
        "points": points,
        "stats": stats,
        "jump_segments": jump_segments,
        "risk": risk,
        "summary": summary,
    }


def extract_payload_points(payload):
    points = []
    if not isinstance(payload, list):
        return points

    for run in payload:
        if not isinstance(run, dict):
            continue
        for track_index, track in enumerate(run.get("tracks", []) or []):
            if not isinstance(track, dict):
                continue
            for point in track.get("points", []) or []:
                if not isinstance(point, dict):
                    continue
                lat_lng = point.get("latLng", {})
                try:
                    lat = float(lat_lng["latitude"])
                    lng = float(lat_lng["longitude"])
                    locatetime = int(point["locatetime"])
                except (KeyError, TypeError, ValueError):
                    continue
                points.append({
                    "lng": lng,
                    "lat": lat,
                    "display_lng": lng - UPLOAD_LONGITUDE_OFFSET,
                    "display_lat": lat - UPLOAD_LATITUDE_OFFSET,
                    "time": locatetime,
                    "track_index": track_index,
                })
    return points


def update_preview_status(preview, status):
    updated = dict(preview or {})
    updated["status"] = status
    updated["summary"] = format_preview_summary(updated)
    return updated


def format_preview_summary(preview):
    if not preview or not preview.get("available"):
        return "暂无可预览路线"

    stats = preview.get("stats", {})
    run_index = preview.get("run_index")
    total_runs = preview.get("total_runs")
    prefix = f"第{run_index}/{total_runs}条：" if run_index and total_runs else ""
    distance_km = (stats.get("distance_m") or 0.0) / 1000.0
    point_count = stats.get("point_count") or 0
    jump_count = stats.get("jump_count") or 0
    status = preview.get("status") or "待上传"
    risk = preview.get("risk") or {}
    risk_part = ""
    if risk.get("score") is not None:
        risk_part = f" / {risk.get('level_label', '风险')} {risk['score']}"
    return f"{prefix}{distance_km:.2f}km / {point_count}点 / {jump_count}处跳段{risk_part} / {status}"


def generate_route_preview_html(preview, baidu_ak=BAIDU_MAP_AK):
    points = preview.get("points", []) if preview else []
    jumps = preview.get("jump_segments", []) if preview else []
    stats = preview.get("stats", {}) if preview else {}
    risk = preview.get("risk", {}) if preview else {}

    safe_summary = html.escape(format_preview_summary(preview))
    safe_status = html.escape(preview.get("status", "未知") if preview else "未知")
    data_json = json.dumps(points, ensure_ascii=False)
    jumps_json = json.dumps(jumps, ensure_ascii=False)

    distance_km = (stats.get("distance_m") or 0.0) / 1000.0
    duration_min = (stats.get("duration_sec") or 0.0) / 60.0
    risk_text = ""
    if risk.get("score") is not None:
        risk_text = f"{risk.get('score')}/100（{risk.get('level_label', '未知')}）"
    else:
        risk_text = "未检测"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>实际上传路线预览</title>
    <style>
        html, body, #map {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
            font-family: Arial, "Microsoft YaHei", sans-serif;
        }}
        #panel {{
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 1000;
            width: 300px;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid rgba(15, 23, 42, 0.14);
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
            padding: 12px 14px;
            color: #172033;
            font-size: 13px;
            line-height: 1.5;
        }}
        #panel h1 {{
            margin: 0 0 8px;
            font-size: 15px;
        }}
        #panel .muted {{
            color: #667085;
        }}
        #panel .warn {{
            color: #b42318;
            font-weight: 700;
        }}
        #empty {{
            display: none;
            position: absolute;
            inset: 0;
            align-items: center;
            justify-content: center;
            color: #475467;
            background: #f8fafc;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="empty">暂无可预览路线</div>
    <div id="panel">
        <h1>实际上传路线</h1>
        <div class="muted">{safe_summary}</div>
        <div>状态：{safe_status}</div>
        <div>距离：{distance_km:.2f} km</div>
        <div>时长：{duration_min:.1f} min</div>
        <div>点数：{stats.get("point_count", 0)} 个</div>
        <div>起终点距离：{stats.get("start_end_m", 0.0):.1f} m</div>
        <div class="warn">跳段：{stats.get("jump_count", 0)} 处，最长 {stats.get("max_segment_m", 0.0):.1f} m</div>
        <div>风险：{html.escape(risk_text)}</div>
        <div class="muted">地图显示已反向应用 GPS 校正，统计仍按上传坐标计算。</div>
    </div>
    <script type="text/javascript" src="https://api.map.baidu.com/api?v=3.0&ak={html.escape(baidu_ak)}"></script>
    <script>
        var routePoints = {data_json};
        var jumpSegments = {jumps_json};

        if (!routePoints || routePoints.length < 2) {{
            document.getElementById("empty").style.display = "flex";
        }} else {{
            var map = new BMap.Map("map");
            var bPoints = routePoints.map(function(p) {{
                return new BMap.Point(p.display_lng || p.lng, p.display_lat || p.lat);
            }});
            map.centerAndZoom(bPoints[0], 16);
            map.enableScrollWheelZoom(true);
            map.addControl(new BMap.NavigationControl());
            map.addControl(new BMap.ScaleControl());
            map.addControl(new BMap.MapTypeControl());

            var routeLine = new BMap.Polyline(bPoints, {{
                strokeColor: "#2563eb",
                strokeWeight: 5,
                strokeOpacity: 0.82
            }});
            map.addOverlay(routeLine);

            jumpSegments.forEach(function(seg) {{
                var jumpLine = new BMap.Polyline([
                    new BMap.Point((seg.display_from || seg.from).lng, (seg.display_from || seg.from).lat),
                    new BMap.Point((seg.display_to || seg.to).lng, (seg.display_to || seg.to).lat)
                ], {{
                    strokeColor: "#dc2626",
                    strokeWeight: 6,
                    strokeOpacity: 0.9
                }});
                map.addOverlay(jumpLine);
            }});

            var startMarker = new BMap.Marker(bPoints[0]);
            var endMarker = new BMap.Marker(bPoints[bPoints.length - 1]);
            map.addOverlay(startMarker);
            map.addOverlay(endMarker);
            startMarker.setTitle("起点");
            endMarker.setTitle("终点");
            map.setViewport(bPoints, {{ margins: [70, 360, 40, 40] }});
        }}
    </script>
</body>
</html>"""


def _track_count(payload):
    if not isinstance(payload, list):
        return 0
    return sum(len(run.get("tracks", []) or []) for run in payload if isinstance(run, dict))


def _risk_summary(risk_analysis):
    if not risk_analysis:
        return {}
    return {
        "score": risk_analysis.get("score"),
        "level": risk_analysis.get("level"),
        "level_label": risk_analysis.get("level_label"),
    }
