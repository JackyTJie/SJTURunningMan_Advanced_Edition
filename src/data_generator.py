import math
import uuid
import time
import random
import os
from utils.auxiliary_util import haversine_distance, log_output, TRACK_POINT_DECIMAL_PLACES, get_current_epoch_ms, SportsUploaderError

def read_gps_coordinates_from_file(file_path):
    """
    从default.txt文件中读取GPS坐标
    返回格式为[(longitude, latitude), ...]的列表
    """
    coordinates = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lon, lat = line.split(',')
                        coordinates.append((float(lon), float(lat)))
                    except ValueError:
                        log_output(f"无法解析坐标行: {line}", "warning")
                        continue
    except FileNotFoundError:
        log_output(f"找不到文件: {file_path}", "error")
        raise SportsUploaderError(f"找不到位置文件: {file_path}")
    except Exception as e:
        log_output(f"读取位置文件时出错: {e}", "error")
        raise SportsUploaderError(f"读取位置文件时出错: {e}")
    
    if not coordinates:
        raise SportsUploaderError("GPS坐标文件为空或格式错误")
    
    return coordinates


def generate_baidu_map_html(ak="MYUXpppuOOvq99cP2AmDvplAW76VV8vr"):
    """
    生成百度地图HTML页面用于坐标采集
    """
    html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>路线规划器</title>
    <style>
        body, html, #map-container {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100vh;
            overflow: hidden;
            font-family: Arial, sans-serif;
        }}
        #info {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
            max-width: 350px;
            max-height: 80vh;
            overflow-y: auto;
            font-size: 14px;
        }}
        #coordinate-list {{
            max-height: 300px;
            overflow-y: auto;
            margin-top: 10px;
            font-size: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 5px;
            background: #f9f9f9;
        }}
        .coord-item {{
            padding: 5px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }}
        .coord-item:hover {{
            background-color: #f5f5f5;
        }}
        .coord-item:last-child {{
            border-bottom: none;
        }}
        .warning {{
            color: #d63031;
            font-size: 12px;
            margin: 5px 0;
            padding: 5px;
            background: #ffeaa7;
            border-radius: 3px;
        }}
        .success {{
            color: #00b894;
            font-size: 12px;
            margin: 5px 0;
            padding: 5px;
            background: #55efc4;
            border-radius: 3px;
        }}
        button {{
            background: #0984e3;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            margin: 2px;
            font-size: 12px;
        }}
        button:hover {{
            background: #0767b3;
        }}
        button.clear {{
            background: #d63031;
        }}
        button.clear:hover {{
            background: #b02525;
        }}
        button.save {{
            background: #00b894;
        }}
        button.save:hover {{
            background: #009a7a;
        }}
        .control-group {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div id="info">
        <h3>🗺️ 路线规划器</h3>
        <p>点击地图任意位置采集坐标点，形成跑步路线</p>

        <div class="control-group">
            <button onclick="clearAllMarkers()" class="clear">清空所有点</button>
            <button onclick="exportCoordinates()" class="save">保存路线</button>
        </div>

        <div class="success" id="status">地图加载中...</div>

        <div id="coordinate-list">
            <div style="text-align: center; color: #666; padding: 20px;">
                点击地图开始采集坐标...
            </div>
        </div>
    </div>
    <div id="map-container"></div>

    <script type="text/javascript" src="https://api.map.baidu.com/api?v=3.0&ak={ak}"></script>
    <script>
        // 初始化地图
        var map = new BMap.Map("map-container");
        var statusDiv = document.getElementById('status');
        var coordinateList = document.getElementById('coordinate-list');

        // 设置中心点（上海交通大学闵行校区附近）
        var point = new BMap.Point(121.442938, 31.031599);
        map.centerAndZoom(point, 15);

        // 启用滚轮缩放
        map.enableScrollWheelZoom(true);

        // 存储坐标的数组
        var coordinates = [];
        var markers = [];

        // 地图加载成功回调
        map.addEventListener("tilesloaded", function() {{
            statusDiv.innerHTML = "✓ 地图加载成功，点击地图开始采集坐标";
            statusDiv.className = "success";
        }});

        // 添加地图点击事件
        map.addEventListener("click", function(e) {{
            var lng = e.point.lng;
            var lat = e.point.lat;

            // 保存坐标
            var coord = {{
                lng: lng,
                lat: lat,
                timestamp: Date.now()
            }};
            coordinates.push(coord);

            // 在点击位置添加标记
            var marker = new BMap.Marker(e.point);
            map.addOverlay(marker);
            markers.push(marker);

            // 添加标记点击事件（删除标记）
            marker.addEventListener("click", function() {{
                map.removeOverlay(marker);
                // 从坐标数组中移除
                var index = coordinates.findIndex(c =>
                    Math.abs(c.lng - lng) < 0.000001 && Math.abs(c.lat - lat) < 0.000001);
                if (index > -1) {{
                    coordinates.splice(index, 1);
                }}
                // 从标记数组中移除
                var markerIndex = markers.indexOf(marker);
                if (markerIndex > -1) {{
                    markers.splice(markerIndex, 1);
                }}
                updateCoordinateList();
            }});

            // 显示坐标信息
            var infoWindow = new BMap.InfoWindow(
                "经度: " + lng.toFixed(6) + "<br/>纬度: " + lat.toFixed(6) +
                "<br/><small>点击标记可删除</small>"
            );
            marker.openInfoWindow(infoWindow);

            // 更新坐标列表显示
            updateCoordinateList();
        }});

        // 更新坐标列表显示
        function updateCoordinateList() {{
            coordinateList.innerHTML = '';

            if (coordinates.length === 0) {{
                coordinateList.innerHTML = '<div style="text-align: center; color: #666; padding: 20px;">点击地图开始采集坐标...</div>';
                return;
            }}

            coordinates.forEach(function(coord, index) {{
                var coordDiv = document.createElement('div');
                coordDiv.className = 'coord-item';
                coordDiv.innerHTML =
                    '<strong>#' + (index + 1) + '</strong><br/>' +
                    '经度: ' + coord.lng.toFixed(6) + '<br/>' +
                    '纬度: ' + coord.lat.toFixed(6);
                coordinateList.appendChild(coordDiv);
            }});
        }}

        // 清空所有标记
        function clearAllMarkers() {{
            // 移除所有标记
            markers.forEach(function(marker) {{
                map.removeOverlay(marker);
            }});
            markers = [];
            coordinates = [];
            updateCoordinateList();
            statusDiv.innerHTML = "所有坐标已清空";
            statusDiv.className = "success";
        }}

        // 导出坐标为文件
        function exportCoordinates() {{
            if (coordinates.length < 2) {{
                alert("请至少选择2个坐标点！");
                return;
            }}

            let coordText = "";
            coordinates.forEach(function(coord) {{
                coordText += coord.lng + "," + coord.lat + "\\n";
            }});

            // Create download link
            var blob = new Blob([coordText], {{ type: 'text/plain' }});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'user.txt';
            document.body.appendChild(a);
            
            // Show instructions to save in project folder
            statusDiv.innerHTML = '✓ 点击下面按钮下载user.txt，<br/>请将文件保存到项目根目录！ (' + coordinates.length + '个点)';
            statusDiv.className = "success";
            
            // Programmatically click the link
            a.click();
            
            // Clean up
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        // 添加缩放控件
        map.addControl(new BMap.NavigationControl());
        map.addControl(new BMap.ScaleControl());
        map.addControl(new BMap.MapTypeControl());
    </script>
</body>
</html>
    '''
    
    # 保存HTML文件
    html_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'route_planner.html')
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_file_path


def interpolate_between_points(start_point, end_point, distance_interval):
    """
    在两个点之间按指定距离间隔插入中间点
    """
    start_lon, start_lat = start_point
    end_lon, end_lat = end_point
    
    # 计算两点间距离
    total_distance = haversine_distance(start_lat, start_lon, end_lat, end_lon)
    
    if total_distance == 0 or distance_interval <= 0:
        return []
    
    # 计算需要插入的点数
    num_intervals = int(total_distance / distance_interval)
    if num_intervals <= 0:
        return []
    
    interpolated_points = []
    
    for i in range(1, num_intervals + 1):
        fraction = i / (num_intervals + 1)  # +1 to exclude the start/end points
        
        # 线性插值
        interp_lat = start_lat + fraction * (end_lat - start_lat)
        interp_lon = start_lon + fraction * (end_lon - start_lon)
        
        interpolated_points.append((interp_lon, interp_lat))
    
    return interpolated_points


def calculate_route_distance(coordinates):
    """
    计算路径总距离
    """
    if len(coordinates) < 2:
        return 0
    
    total_distance = 0
    for i in range(len(coordinates) - 1):
        lon1, lat1 = coordinates[i]
        lon2, lat2 = coordinates[i + 1]
        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
    
    return total_distance


def adjust_path_for_speed(coordinates, target_speed_mps, target_distance_m, interval_seconds, log_cb=None):
    """
    根据目标速度调整路径，根据路径长度选择不同策略
    优化版本：创建原始坐标与百分比的映射关系，使用百分比来选择剩余距离的坐标点
    """
    if not coordinates:
        return []

    # 如果坐标点太少，直接返回原坐标
    if len(coordinates) < 2:
        return coordinates

    # 计算当前路径总长度和累积距离
    current_total_distance = 0
    distance_cumulative = [0]  # 累积距离列表，对应每个原始坐标点
    for i in range(len(coordinates) - 1):
        lon1, lat1 = coordinates[i]
        lon2, lat2 = coordinates[i + 1]
        seg_distance = haversine_distance(lat1, lon1, lat2, lon2)
        current_total_distance += seg_distance
        distance_cumulative.append(current_total_distance)

    # 首先生成一个循环的详细坐标数据，并计算一次距离
    distance_interval_for_sampling = target_speed_mps * interval_seconds  # 每个间隔应该走的距离

    detailed_coordinates = [coordinates[0]]  # Start with first coordinate

    for i in range(len(coordinates) - 1):
        start_point = coordinates[i]
        end_point = coordinates[i + 1]

        # Insert intermediate points based on the distance interval
        intermediate_points = interpolate_between_points(start_point, end_point, distance_interval_for_sampling)

        # Add the intermediate points
        detailed_coordinates.extend(intermediate_points)
        # Add the end point
        detailed_coordinates.append(end_point)

    # 计算一个循环的详细距离
    single_loop_distance = 0
    for i in range(len(detailed_coordinates) - 1):
        lon1, lat1 = detailed_coordinates[i]
        lon2, lat2 = detailed_coordinates[i + 1]
        single_loop_distance += haversine_distance(lat1, lon1, lat2, lon2)

    # 计算起点和终点之间的直线距离
    start_lon, start_lat = detailed_coordinates[0]
    end_lon, end_lat = detailed_coordinates[-1]
    start_end_dist = haversine_distance(start_lat, start_lon, end_lat, end_lon)

    # 使用 compensation (only fixed 200m)
    compensated_target_distance = target_distance_m + 200  # Add 200m compensation only

    adjusted_coordinates = []

    if single_loop_distance > compensated_target_distance:
        # 路径太长，发送特殊消息给UI以显示对话框
        # Show target in the special message for UI handling
        original_target = target_distance_m  # Original target without compensation for message
        log_output(f"SPECIAL_ROUTE_TOO_LONG:{single_loop_distance}:{original_target}", "warning", log_cb)
        log_output(f"警告: 单次路径长度为 {single_loop_distance:.2f}m，超过了目标距离 {original_target}m (with compensation)", "warning", log_cb)
        log_output(f"提示: 建议缩短路径以符合要求", "info", log_cb)

        # Truncate the path to the compensated target distance
        adjusted_coordinates = []
        current_distance = 0
        for i in range(len(detailed_coordinates) - 1):
            lon1, lat1 = detailed_coordinates[i]
            lon2, lat2 = detailed_coordinates[i + 1]
            seg_distance = haversine_distance(lat1, lon1, lat2, lon2)

            if current_distance + seg_distance <= compensated_target_distance:
                # If adding the complete segment doesn't exceed the target, add it
                if not adjusted_coordinates or adjusted_coordinates[-1] != (lon1, lat1):
                    adjusted_coordinates.append((lon1, lat1))
                current_distance += seg_distance
            else:
                # Calculate the exact endpoint within the target distance
                remaining_dist_in_seg = compensated_target_distance - current_distance
                if seg_distance > 0:
                    fraction = remaining_dist_in_seg / seg_distance
                    final_lat = lat1 + fraction * (lat2 - lat1)
                    final_lon = lon1 + fraction * (lon2 - lon1)
                    adjusted_coordinates.append((final_lon, final_lat))
                current_distance = compensated_target_distance
                break
    elif single_loop_distance < compensated_target_distance:
        # 路径较短，根据起点终点距离选择策略
        # 计算起点和终点之间的直线距离
        start_lon, start_lat = detailed_coordinates[0]
        end_lon, end_lat = detailed_coordinates[-1]
        start_end_dist = haversine_distance(start_lat, start_lon, end_lat, end_lon)

        if start_end_dist > 15:  # A-B距离大于15米，使用A-B B-A A-B...策略
            log_output(f"采用往返策略: 起终点距离 {start_end_dist:.2f}m > 15m", "info", log_cb)

            # 计算往返一次的距离（A-B + B-A）
            round_trip_distance = single_loop_distance * 2  # 正向路径加上反向路径
            
            # 使用除法计算需要多少个完整的往返和剩余距离
            if round_trip_distance > 0:
                num_complete_round_trips = int(compensated_target_distance / round_trip_distance)
                
                # Calculate remaining distance for percentage calculation
                remaining_distance = compensated_target_distance % round_trip_distance
            
                # 添加完整的往返循环
                for _ in range(num_complete_round_trips):
                    # 添加正向路径 (A-B)
                    adjusted_coordinates.extend(detailed_coordinates)
                    # 添加反向路径 (B-A)
                    adjusted_coordinates.extend(detailed_coordinates[::-1])
                
                # 添加余数部分 using distance accumulation
                if remaining_distance > 0:
                    # Calculate what percentage of a round trip the remaining distance represents
                    percentage_of_round_trip = remaining_distance / round_trip_distance
                    
                    if percentage_of_round_trip <= 0.5:
                        # Use forward direction (A-B), accumulating distance
                        accumulated_distance = 0
                        partial_coords = []
                        
                        # Add points until we reach the required remaining distance
                        for i in range(len(detailed_coordinates) - 1):
                            lon1, lat1 = detailed_coordinates[i]
                            lon2, lat2 = detailed_coordinates[i + 1]
                            seg_distance = haversine_distance(lat1, lon1, lat2, lon2)

                            if accumulated_distance + seg_distance <= remaining_distance:
                                # If adding the complete segment doesn't exceed the remaining distance, add it
                                if not partial_coords or partial_coords[-1] != (lon1, lat1):
                                    partial_coords.append((lon1, lat1))
                                accumulated_distance += seg_distance
                            else:
                                # Calculate the exact endpoint within the remaining distance
                                remaining_dist_in_seg = remaining_distance - accumulated_distance
                                if seg_distance > 0:
                                    fraction = remaining_dist_in_seg / seg_distance
                                    final_lat = lat1 + fraction * (lat2 - lat1)
                                    final_lon = lon1 + fraction * (lon2 - lon1)
                                    partial_coords.append((final_lon, final_lat))
                                break
                        
                        if partial_coords:
                            # Avoid duplicate connection point
                            if adjusted_coordinates and partial_coords and adjusted_coordinates[-1] == partial_coords[0]:
                                adjusted_coordinates.extend(partial_coords[1:])
                            else:
                                adjusted_coordinates.extend(partial_coords)
                    else:
                        # Use forward loop + backward partial
                        # Add full forward loop first 
                        forward_coords = detailed_coordinates[:]
                        adjusted_coordinates.extend(forward_coords)
                        
                        # Then add partial backward portion using distance accumulation
                        remaining_backward_distance = remaining_distance - (single_loop_distance)  # Remaining after full forward loop
                        accumulated_distance = 0
                        partial_reverse_coords = []
                        
                        # Use reversed coordinates for backward direction
                        reversed_coords = detailed_coordinates[::-1]
                        
                        # Add points in reverse direction until we reach the required remaining distance
                        for i in range(len(reversed_coords) - 1):
                            lon1, lat1 = reversed_coords[i]
                            lon2, lat2 = reversed_coords[i + 1]
                            seg_distance = haversine_distance(lat1, lon1, lat2, lon2)

                            if accumulated_distance + seg_distance <= remaining_backward_distance:
                                # If adding the complete segment doesn't exceed the remaining distance, add it
                                if not partial_reverse_coords or partial_reverse_coords[-1] != (lon1, lat1):
                                    partial_reverse_coords.append((lon1, lat1))
                                accumulated_distance += seg_distance
                            else:
                                # Calculate the exact endpoint within the remaining distance
                                remaining_dist_in_seg = remaining_backward_distance - accumulated_distance
                                if seg_distance > 0:
                                    fraction = remaining_dist_in_seg / seg_distance
                                    final_lat = lat1 + fraction * (lat2 - lat1)
                                    final_lon = lon1 + fraction * (lon2 - lon1)
                                    partial_reverse_coords.append((final_lon, final_lat))
                                break
                        
                        if partial_reverse_coords:
                            # Remove the first point to avoid duplication if needed
                            if adjusted_coordinates and partial_reverse_coords and adjusted_coordinates[-1] == partial_reverse_coords[0]:
                                adjusted_coordinates.extend(partial_reverse_coords[1:])
                            else:
                                adjusted_coordinates.extend(partial_reverse_coords)
            else:
                # Fallback if round_trip_distance is zero, just add single loop and keep going
                adjusted_coordinates.extend(detailed_coordinates)
                current_distance = single_loop_distance
                
                # Add more loops as needed
                while current_distance < target_distance:
                    reverse_coordinates = detailed_coordinates[::-1]
                    for i in range(len(reverse_coordinates) - 1):
                        lon1, lat1 = reverse_coordinates[i]
                        lon2, lat2 = reverse_coordinates[i + 1]
                        seg_distance = haversine_distance(lat1, lon1, lat2, lon2)

                        if current_distance + seg_distance <= target_distance:
                            if not adjusted_coordinates or adjusted_coordinates[-1] != (lon1, lat1):
                                adjusted_coordinates.append((lon1, lat1))
                            current_distance += seg_distance
                        else:
                            remaining_dist_in_seg = target_distance - current_distance
                            if seg_distance > 0:
                                fraction = remaining_dist_in_seg / seg_distance
                                final_lat = lat1 + fraction * (reverse_coordinates[i + 1][1] - lat1)
                                final_lon = lon1 + fraction * (reverse_coordinates[i + 1][0] - lon1)
                                adjusted_coordinates.append((final_lon, final_lat))
                            break
                    
                    if current_distance >= target_distance:
                        break
                        
                    for i in range(len(detailed_coordinates) - 1):
                        lon1, lat1 = detailed_coordinates[i]
                        lon2, lat2 = detailed_coordinates[i + 1]
                        seg_distance = haversine_distance(lat1, lon1, lat2, lon2)

                        if current_distance + seg_distance <= target_distance:
                            if not adjusted_coordinates or adjusted_coordinates[-1] != (lon1, lat1):
                                adjusted_coordinates.append((lon1, lat1))
                            current_distance += seg_distance
                        else:
                            remaining_dist_in_seg = target_distance - current_distance
                            if seg_distance > 0:
                                fraction = remaining_dist_in_seg / seg_distance
                                final_lat = lat1 + fraction * (lat2 - lat1)
                                final_lon = lon1 + fraction * (lon2 - lon1)
                                adjusted_coordinates.append((final_lon, final_lat))
                            break
        else:  # A-B距离小于等于15米，使用A-B-A-B...循环策略（形成环路）
            log_output(f"采用环路策略: 起终点距离 {start_end_dist:.2f}m <= 15m", "info", log_cb)

            # 使用除法计算需要多少个循环和剩余距离
            if single_loop_distance > 0:
                num_complete_loops = int(compensated_target_distance / single_loop_distance)
                
                # Calculate remaining distance for percentage calculation
                remaining_distance = compensated_target_distance % single_loop_distance

                # 添加完整循环
                for _ in range(num_complete_loops):
                    adjusted_coordinates.extend(detailed_coordinates)

                # 添加余数部分 using distance accumulation
                if remaining_distance > 0 and len(detailed_coordinates) > 1:
                    accumulated_distance = 0
                    partial_coords = []
                    
                    # Add points until we reach the required remaining distance
                    for i in range(len(detailed_coordinates) - 1):
                        lon1, lat1 = detailed_coordinates[i]
                        lon2, lat2 = detailed_coordinates[i + 1]
                        seg_distance = haversine_distance(lat1, lon1, lat2, lon2)

                        if accumulated_distance + seg_distance <= remaining_distance:
                            # If adding the complete segment doesn't exceed the remaining distance, add it
                            if not partial_coords or partial_coords[-1] != (lon1, lat1):
                                partial_coords.append((lon1, lat1))
                            accumulated_distance += seg_distance
                        else:
                            # Calculate the exact endpoint within the remaining distance
                            remaining_dist_in_seg = remaining_distance - accumulated_distance
                            if seg_distance > 0:
                                fraction = remaining_dist_in_seg / seg_distance
                                final_lat = lat1 + fraction * (lat2 - lat1)
                                final_lon = lon1 + fraction * (lon2 - lon1)
                                partial_coords.append((final_lon, final_lat))
                            break
                    
                    if partial_coords:
                        # Avoid duplicate connection point
                        if adjusted_coordinates and partial_coords and adjusted_coordinates[-1] == partial_coords[0]:
                            adjusted_coordinates.extend(partial_coords[1:])
                        else:
                            adjusted_coordinates.extend(partial_coords)
            else:
                # Fallback if single_loop_distance is zero
                adjusted_coordinates.extend(detailed_coordinates)
    else:
        # 距离正好等于目标距离
        adjusted_coordinates = detailed_coordinates[:]

    # 计算实际的总距离
    actual_distance = 0
    if len(adjusted_coordinates) > 1:
        for i in range(len(adjusted_coordinates) - 1):
            lon1, lat1 = adjusted_coordinates[i]
            lon2, lat2 = adjusted_coordinates[i + 1]
            actual_distance += haversine_distance(lat1, lon1, lat2, lon2)

    # 确保至少有一个点
    if len(adjusted_coordinates) == 0 and len(coordinates) > 0:
        adjusted_coordinates = coordinates[:]

    # 记录实际速度
    actual_speed = actual_distance / (actual_distance / target_speed_mps) if actual_distance > 0 and target_speed_mps > 0 else target_speed_mps
    log_output(f"原始路径长度: {current_total_distance:.2f}m, 单次循环长度: {single_loop_distance:.2f}m, 最终长度: {actual_distance:.2f}m, 实际速度: {actual_speed:.2f}m/s, 目标速度: {target_speed_mps:.2f}m/s", "info", log_cb)

    return adjusted_coordinates
def split_track_into_segments(all_points_with_time, total_duration_sec, min_segment_points=5, stop_check_cb=None):
    """
    将所有带有locatetime的轨迹点拆分为多个轨迹段。
    并分配不同的 status 和 tstate。
    """
    tracks = []

    status_map = {
        "normal": "0",
        "stop": "0",
        "invalid": "2",
    }

    current_start_point_idx = 0

    if not all_points_with_time:
        return tracks

    while current_start_point_idx < len(all_points_with_time):
        if stop_check_cb and stop_check_cb():
            log_output("轨迹生成被中断。", "warning")
            raise SportsUploaderError("任务已停止。")

        segment_points = []

        remaining_points = len(all_points_with_time) - current_start_point_idx
        if remaining_points <= min_segment_points:
            segment_length = remaining_points
        else:
            segment_length = random.randint(min_segment_points, max(min_segment_points, remaining_points // 3))
            if segment_length == 1 and remaining_points > 1:
                segment_length = min_segment_points

        segment_points = all_points_with_time[current_start_point_idx: current_start_point_idx + segment_length]
        current_start_point_idx += segment_length

        if not segment_points:
            continue

        rand_val = random.random()
        if rand_val < 0.8:
            segment_status = "normal"
        elif rand_val < 0.9:
            segment_status = "invalid"
        else:
            segment_status = "stop"

        segment_tstate = status_map.get(segment_status, "0")

        segment_distance = 0
        if len(segment_points) > 1:
            for i in range(len(segment_points) - 1):
                p1 = segment_points[i]['latLng']
                p2 = segment_points[i + 1]['latLng']
                segment_distance += haversine_distance(p1['latitude'], p1['longitude'], p2['latitude'], p2['longitude'])

        segment_start_time_ms = segment_points[0]['locatetime']
        segment_end_time_ms = segment_points[-1]['locatetime']
        segment_duration_sec = math.ceil((segment_end_time_ms - segment_start_time_ms) / 1000)

        tracks.append({
            "counts": len(segment_points),
            "distance": segment_distance,
            "duration": segment_duration_sec,
            "points": segment_points,
            "status": segment_status,
            "trid": str(uuid.uuid4()),
            "tstate": segment_tstate,
            "stime": segment_start_time_ms // 1000,
            "etime": segment_end_time_ms // 1000
        })

    return tracks


def generate_running_data_payload(config, required_signpoints, point_rules_data, log_cb=None, stop_check_cb=None):
    """
    生成符合POST请求体格式的跑步数据，并整合打卡点。
    """
    # 优先从user.txt文件读取GPS坐标（默认路线），如果不存在则使用default.txt（备用路线）
    from utils.auxiliary_util import get_base_path
    base_path = get_base_path()
    
    # Check if a specific route file was provided in config (for CLI)
    config_route_file = config.get('ROUTE_FILE')
    if config_route_file:
        # Use the route file specified in config
        route_path = os.path.join(base_path, config_route_file)
        if os.path.exists(route_path):
            log_output(f"使用配置指定路线文件: {config_route_file}", "info", log_cb)
            original_coordinates = read_gps_coordinates_from_file(route_path)
        else:
            log_output(f"配置指定路线文件不存在: {config_route_file}，尝试默认文件", "warning", log_cb)
            # Fallback to the original logic - load this after
            user_loc_path = os.path.join(base_path, 'user.txt')
            default_loc_path = os.path.join(base_path, 'default.txt')
            
            if os.path.exists(user_loc_path):
                log_output(f"使用当前路线文件: user.txt", "info", log_cb)
                original_coordinates = read_gps_coordinates_from_file(user_loc_path)
            else:
                log_output(f"使用默认路线文件: default.txt", "info", log_cb)
                original_coordinates = read_gps_coordinates_from_file(default_loc_path)
    else:
        # Original behavior: try user.txt, fallback to default.txt
        user_loc_path = os.path.join(base_path, 'user.txt')
        default_loc_path = os.path.join(base_path, 'default.txt')

        if os.path.exists(user_loc_path):
            log_output(f"使用当前路线文件: user.txt", "info", log_cb)
            original_coordinates = read_gps_coordinates_from_file(user_loc_path)
        else:
            log_output(f"使用默认路线文件: default.txt", "info", log_cb)
            original_coordinates = read_gps_coordinates_from_file(default_loc_path)

    # 应用GPS坐标偏移校正
    # 原始坐标：(121.43408070767154, 31.023243657753756) 
    # 当前偏移：(121.44059342261889, 31.02885254751853)
    # 偏移量：经度 +0.00651271494735，纬度 +0.00560888976477
    longitude_offset = -0.00651271494735  # 负值以校正向东偏移
    latitude_offset = -0.00560888976477   # 负值以校正向北偏移
    
    corrected_coordinates = []
    for lon, lat in original_coordinates:
        corrected_lon = lon + longitude_offset
        corrected_lat = lat + latitude_offset
        corrected_coordinates.append((corrected_lon, corrected_lat))
    
    original_coordinates = corrected_coordinates
    log_output(f"GPS坐标已校正，共 {len(corrected_coordinates)} 个坐标点", "info", log_cb)
    
    # 应用额外的微调校正 - 解决地图选择坐标与实际记录坐标不一致的问题
    # 在用户反馈中，选择坐标后实际记录坐标与选择坐标有差异
    # 根据实测数据调整坐标偏差：显示坐标(121.4360659628486,31.024821917009408) -> 实际应为(121.43630401380874,31.02476776149208)
    # 计算所需校正值：经度+0.000238，纬度-0.000054
    # 总计校正值（原始微调+精确校正）：经度-0.000144+0.000094=+0.000094，纬度-0.000646-0.000054=-0.000700
    additional_longitude_offset = 0.000094  # 额外的经度校正（原始微调+精确校正）
    additional_latitude_offset = -0.000700   # 额外的纬度校正（原始微调+精确校正）
    
    final_coordinates = []
    for lon, lat in original_coordinates:
        final_lon = lon + additional_longitude_offset
        final_lat = lat + additional_latitude_offset
        final_coordinates.append((final_lon, final_lat))
    
    original_coordinates = final_coordinates
    log_output(f"GPS坐标微调校正完成，共 {len(final_coordinates)} 个坐标点", "info", log_cb)

    # 目标参数
    target_distance_km = config.get('RUN_DISTANCE_KM', 5)  # 从配置获取目标距离，默认5km
    target_distance_m = target_distance_km * 1000  # 转换为米
    pace_sec_per_km = 4 * 60  # 4 分钟每公里 -> 秒/公里 (对应 15 km/h)
    total_duration_sec = int(round(pace_sec_per_km * target_distance_km))
    interval_seconds = int(config.get('INTERVAL_SECONDS', 3))
    if interval_seconds <= 0:
        interval_seconds = 3

    # 计算目标速度（m/s）
    target_speed_mps = target_distance_m / total_duration_sec if total_duration_sec > 0 else config.get('RUNNING_SPEED_MPS', 4.17)  # 4.17 m/s ≈ 15 km/h

    # 根据目标速度和距离调整路径
    adjusted_coordinates = adjust_path_for_speed(original_coordinates, target_speed_mps, target_distance_m, interval_seconds, log_cb)

    # 生成带时间戳的轨迹点
    full_interpolated_points_with_time = []
    
    base_start_time_ms = config['START_TIME_EPOCH_MS'] if config.get('START_TIME_EPOCH_MS') is not None else get_current_epoch_ms()
    current_locatetime_ms = base_start_time_ms

    # 按照间隔时间生成轨迹点
    total_path_distance = 0
    for i in range(len(adjusted_coordinates)):
        if stop_check_cb and stop_check_cb():
            log_output("轨迹生成被中断。", "warning")
            raise SportsUploaderError("任务已停止。")

        lon, lat = adjusted_coordinates[i]

        # 计算到当前点的累计距离
        if i > 0:
            prev_lon, prev_lat = adjusted_coordinates[i-1]
            segment_distance = haversine_distance(prev_lat, prev_lon, lat, lon)
            total_path_distance += segment_distance

        # 计算当前点的时间戳 (基于距离和速度)
        # 假设以恒定速度运行
        if target_speed_mps > 0:
            elapsed_time_sec = total_path_distance / target_speed_mps
            current_locatetime_ms = base_start_time_ms + int(elapsed_time_sec * 1000)

        formatted_lat = f"{lat:.{TRACK_POINT_DECIMAL_PLACES}f}"
        formatted_lon = f"{lon:.{TRACK_POINT_DECIMAL_PLACES}f}"

        point = {
            "latLng": {"latitude": float(formatted_lat), "longitude": float(formatted_lon)},
            "location": f"{formatted_lon},{formatted_lat}",
            "step": 0,
            "locatetime": current_locatetime_ms
        }

        full_interpolated_points_with_time.append(point)

    # 计算实际距离和时长
    actual_total_distance = 0
    if len(full_interpolated_points_with_time) > 1:
        for i in range(len(full_interpolated_points_with_time) - 1):
            p1 = full_interpolated_points_with_time[i]['latLng']
            p2 = full_interpolated_points_with_time[i + 1]['latLng']
            actual_total_distance += haversine_distance(p1['latitude'], p1['longitude'], p2['latitude'], p2['longitude'])

    actual_total_duration_sec = 0
    if full_interpolated_points_with_time:
        first_point_time_ms = full_interpolated_points_with_time[0]['locatetime']
        last_point_time_ms = full_interpolated_points_with_time[-1]['locatetime']
        actual_total_duration_sec = max(1, int((last_point_time_ms - first_point_time_ms) / 1000))

    # 按时间分段处理轨迹
    tracks_list = split_track_into_segments(full_interpolated_points_with_time, actual_total_duration_sec, stop_check_cb=stop_check_cb)

    run_id = point_rules_data.get('rules', {}).get('id', 6)
    if run_id == 6:
        run_id = 9

    sp_avg = 0
    if actual_total_distance > 0 and actual_total_duration_sec > 0:
        sp_avg = actual_total_duration_sec / (actual_total_distance / 1000) / 60
        sp_avg = round(sp_avg)

    rules_meta = point_rules_data.get('rules', {})
    min_sp_s_per_km = rules_meta.get('spmin', 180)
    max_sp_s_per_km = rules_meta.get('spmax', 540)

    sp_avg_s_per_km = sp_avg * 60 if sp_avg > 0 else 0

    if actual_total_distance > 0:
        if sp_avg_s_per_km < min_sp_s_per_km:
            log_output(f"Warning: Calculated pace {sp_avg} min/km ({sp_avg_s_per_km:.0f} s/km) is faster than {min_sp_s_per_km / 60:.0f} min/km ({min_sp_s_per_km:.0f} s/km). Adjusting to minimum allowed pace.", "warning", log_cb)
            sp_avg = math.ceil(min_sp_s_per_km / 60)
        elif sp_avg_s_per_km > max_sp_s_per_km:
            log_output(f"Warning: Calculated pace {sp_avg} min/km ({sp_avg_s_per_km:.0f} s/km) is slower than {max_sp_s_per_km / 60:.0f} min/km ({max_sp_s_per_km:.0f} s/km). Adjusting to maximum allowed pace.", "warning", log_cb)
            sp_avg = math.floor(max_sp_s_per_km / 60)

    request_body = [
        {
            "fravg": 0,
            "id": run_id,
            "sid": str(uuid.uuid4()),
            "signpoints": [],
            "spavg": sp_avg,
            "state": "0",
            "tracks": tracks_list,
            "userId": config['USER_ID']
        }
    ]
    return request_body, actual_total_distance, actual_total_duration_sec