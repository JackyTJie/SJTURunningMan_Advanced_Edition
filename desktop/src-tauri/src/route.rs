use serde::{Deserialize, Serialize};
use std::{
    fs,
    path::{Path, PathBuf},
};

pub const DEFAULT_ROUTE: &str = include_str!("../../../assets/Routes/default.txt");
pub const MAX_ROUTE_BYTES: u64 = 2 * 1024 * 1024;

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub struct Point {
    pub lon: f64,
    pub lat: f64,
}

#[derive(Clone, Debug)]
pub struct Route {
    pub name: String,
    pub path: Option<PathBuf>,
    pub points: Vec<Point>,
}

pub fn parse(text: &str) -> Result<Vec<Point>, String> {
    let mut points = Vec::new();
    for (index, line) in text.trim_start_matches('\u{feff}').lines().enumerate() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let values: Vec<_> = line.split(',').collect();
        let invalid = || format!("路线第 {} 行无效，应为 longitude,latitude", index + 1);
        if values.len() != 2 {
            return Err(invalid());
        }
        let lon: f64 = values[0].trim().parse().map_err(|_| invalid())?;
        let lat: f64 = values[1].trim().parse().map_err(|_| invalid())?;
        if !lon.is_finite() || !lat.is_finite() || lon.abs() > 180.0 || lat.abs() > 90.0 {
            return Err(invalid());
        }
        let point = Point { lon, lat };
        if points.last() != Some(&point) {
            points.push(point);
        }
        if points.len() > 30_000 {
            return Err("路线不能超过 30,000 个点".into());
        }
    }
    if points.len() < 2 || distance(&points) < 1.0 {
        return Err("路线至少需要 2 个不同的点，长度不少于 1 m".into());
    }
    Ok(points)
}

pub fn read(path: &Path) -> Result<Vec<Point>, String> {
    if fs::metadata(path).map_err(|_| "无法读取路线文件")?.len() > MAX_ROUTE_BYTES {
        return Err("路线文件不能超过 2 MB".into());
    }
    parse(&fs::read_to_string(path).map_err(|_| "路线必须是 UTF-8 文本")?)
}

/// 返回可用路线，以及被跳过的文件说明。
///
/// 单个损坏的 txt 不能让整个列表消失 —— 那会让用户在启动时丢掉所有导入路线。
pub fn list(dir: &Path) -> Result<(Vec<Route>, Vec<String>), String> {
    let mut routes = vec![Route {
        name: "default".into(),
        path: None,
        points: parse(DEFAULT_ROUTE)?,
    }];
    let mut skipped = Vec::new();
    let path = dir.join("routes");
    if path.exists() {
        let mut files: Vec<_> = fs::read_dir(path)
            .map_err(|_| "无法读取路线目录")?
            .filter_map(Result::ok)
            .map(|e| e.path())
            .collect();
        files.sort();
        for path in files {
            if path
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("txt"))
            {
                let name = path.file_name().unwrap_or_default().to_string_lossy();
                match read(&path) {
                    Ok(points) => routes.push(Route {
                        name: path
                            .file_stem()
                            .unwrap_or_default()
                            .to_string_lossy()
                            .into(),
                        path: Some(path),
                        points,
                    }),
                    Err(error) => skipped.push(format!("{name}：{error}")),
                }
            }
        }
    }
    Ok((routes, skipped))
}

pub fn import(dir: &Path, source: &Path) -> Result<String, String> {
    let points = read(source)?;
    let routes_dir = dir.join("routes");
    fs::create_dir_all(&routes_dir).map_err(|_| "无法创建路线目录")?;
    let stem = source
        .file_stem()
        .and_then(|v| v.to_str())
        .ok_or("文件名无效")?;
    let mut name = stem.to_owned();
    let mut index = 1;
    while name == "default" || routes_dir.join(format!("{name}.txt")).exists() {
        name = format!("{stem}_{index}");
        index += 1;
    }
    let text = points
        .iter()
        .map(|p| format!("{:.14},{:.14}\n", p.lon, p.lat))
        .collect::<String>();
    fs::write(routes_dir.join(format!("{name}.txt")), text).map_err(|_| "无法保存路线")?;
    Ok(name)
}

pub fn delete(dir: &Path, route: &Route) -> Result<(), String> {
    let path = route.path.as_ref().ok_or("内置路线不能删除")?;
    let parent = dir
        .join("routes")
        .canonicalize()
        .map_err(|_| "路线目录不存在")?;
    if path.canonicalize().map_err(|_| "路线不存在")?.parent() != Some(parent.as_path()) {
        return Err("只能删除已导入的路线".into());
    }
    fs::remove_file(path).map_err(|_| "无法删除路线".into())
}

pub fn haversine(a: Point, b: Point) -> f64 {
    let dlat = (b.lat - a.lat).to_radians();
    let dlon = (b.lon - a.lon).to_radians();
    let h = (dlat / 2.0).sin().powi(2)
        + a.lat.to_radians().cos() * b.lat.to_radians().cos() * (dlon / 2.0).sin().powi(2);
    6_371_000.0 * 2.0 * h.sqrt().min(1.0).asin()
}

pub fn distance(points: &[Point]) -> f64 {
    points.windows(2).map(|p| haversine(p[0], p[1])).sum()
}
pub fn jumps(points: &[Point]) -> usize {
    points
        .windows(2)
        .filter(|p| haversine(p[0], p[1]) > 150.0)
        .count()
}

pub fn corrected(points: &[Point]) -> Vec<Point> {
    // 保持旧桌面客户端的 BD09 → GCJ02 校准，避免迁移时改变上传坐标。
    points
        .iter()
        .map(|p| Point {
            lon: p.lon - 0.00651271494735 + 0.000094,
            lat: p.lat - 0.00560888976477 - 0.000700,
        })
        .collect()
}

pub fn resample(points: &[Point], target_m: f64, step_m: f64) -> Result<Vec<Point>, String> {
    let route_distance = distance(points);
    if points.len() < 2
        || points.iter().any(|p| {
            !p.lon.is_finite() || !p.lat.is_finite() || p.lon.abs() > 180.0 || p.lat.abs() > 90.0
        })
        || !route_distance.is_finite()
        || route_distance < 1.0
        || !target_m.is_finite()
        || target_m <= 0.0
        // 上限即 settings::MAX_DISTANCE_KM；采样器不再为固定补偿留出余量。
        || target_m > 5_000.0
        || !step_m.is_finite()
        || step_m < 1.0
    {
        return Err("路线或采样参数无效".into());
    }
    let mut cycle = points.to_vec();
    if haversine(points[0], *points.last().unwrap()) > 15.0 {
        cycle.extend(points.iter().rev().skip(1).copied());
    } else if points[0] != *points.last().unwrap() {
        cycle.push(points[0]);
    }
    let lengths: Vec<_> = cycle.windows(2).map(|p| haversine(p[0], p[1])).collect();
    let mut result = vec![cycle[0]];
    let mut traveled = 0.0;
    let mut next_sample = step_m;
    let mut index = 0;
    while traveled < target_m {
        if result.len() > 30_000 {
            return Err("路线过密，生成轨迹超过 30,000 个点，请简化路线".into());
        }
        let length = lengths[index];
        if length > 1e-8 {
            let a = cycle[index];
            let b = cycle[index + 1];
            let end = (traveled + length).min(target_m);
            let interpolate = |position: f64| {
                let fraction = (position - traveled) / length;
                Point {
                    lon: a.lon + (b.lon - a.lon) * fraction,
                    lat: a.lat + (b.lat - a.lat) * fraction,
                }
            };
            while next_sample < end {
                if next_sample > traveled + 1e-8 {
                    result.push(interpolate(next_sample));
                }
                next_sample += step_m;
            }
            // 保留拐点，避免采样跨越弯道后将实际距离缩短。
            result.push(interpolate(end));
            traveled = end;
        }
        index = (index + 1) % lengths.len();
    }
    Ok(result)
}

pub const BAIDU_MAP_AK: &str = "MYUXpppuOOvq99cP2AmDvplAW76VV8vr";
const PREVIEW_TEMPLATE: &str = include_str!("route_preview.html");

pub fn preview_html(points: &[Point], title: &str) -> String {
    let title = if title == "default" {
        "思源湖"
    } else {
        title
    };
    // BD09 原始路线与 GCJ02 payload 在调用端统一为 GCJ02；OpenStreetMap 页面
    // 显示前再转 WGS84。
    let points = serde_json::to_string(points).unwrap_or_else(|_| "[]".into());
    let title = title
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;");
    // 标题最后替换，避免标题里的占位符文本被再次展开。
    PREVIEW_TEMPLATE
        .replace("__POINTS__", &points)
        .replace("__TITLE__", &title)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn validates_route_files() {
        assert!(parse(DEFAULT_ROUTE).unwrap().len() > 20);
        for input in [
            "",
            "1,2",
            "NaN,2\n3,4",
            "181,31\n121,31",
            "1,2,3\n4,5",
            "1,2\n1,2",
        ] {
            assert!(parse(input).is_err());
        }
        assert_eq!(parse("\u{feff}121,31\n\n121.001,31").unwrap().len(), 2);
    }
    #[test]
    fn resampling_goes_back_without_teleporting() {
        let points = parse("121,31\n121.002,31").unwrap();
        let sampled = resample(&points, 1_000.0, 3.0).unwrap();
        assert!(sampled.windows(2).all(|p| haversine(p[0], p[1]) < 3.01));
        assert!((distance(&sampled) - 1_000.0).abs() < 0.1);
        assert!(resample(&points, 1_000.0, 0.0).is_err());
        assert!(resample(
            &[
                Point {
                    lon: f64::NAN,
                    lat: 31.0
                },
                points[0]
            ],
            1_000.0,
            3.0
        )
        .is_err());
    }
    #[test]
    fn resampling_stops_at_the_configured_distance() {
        let points = parse("121,31\n121.002,31").unwrap();
        let sampled = resample(&points, 5_000.0, 3.0).unwrap();
        assert!((distance(&sampled) - 5_000.0).abs() < 0.1);
        assert!(resample(&points, 5_200.0, 3.0).is_err());
    }
    #[test]
    fn preview_escapes_titles_and_maps_only_osm() {
        let points = parse("121,31\n121.1,31").unwrap();
        assert_eq!(jumps(&points), 1);
        let html = preview_html(&points, "<script>");
        assert!(html.contains("&lt;script&gt;"));
        // 预览页固定 OpenStreetMap，不再加载百度或显示引擎切换 / 状态条。
        assert!(!html.contains("api.map.baidu.com"));
        assert!(!html.contains("BMap"));
        assert!(!html.contains("id=\"provider\""));
        assert!(!html.contains("地图引擎"));
        assert!(!html.contains("map-status"));
        assert!(html.contains("L.map('map')"));
        assert!(html.contains("gcj02ToWgs84"));
        assert!(html.contains(">150"));
        assert!(html.contains("https://unpkg.com/leaflet"));
        assert!(html.contains("https://tile.openstreetmap.org/{z}/{x}/{y}.png"));
        assert!(html.contains("strict-origin-when-cross-origin"));
        assert!(!html.contains("https://{s}.tile.openstreetmap.org"));
        assert!(html.contains("https://www.openstreetmap.org/copyright"));
    }

    #[test]
    fn planner_exposes_baidu_and_osm_without_static_leaflet() {
        let html = include_str!("../../../route_planner.html");
        assert!(html.contains("id=\"provider\""));
        assert!(html.contains("value=\"baidu\" selected"));
        assert!(html.contains("value=\"osm\""));
        assert!(html.contains("BMap.Map"));
        assert!(html.contains("wgs84ToBd09"));
        assert!(html.contains("bd09ToWgs84"));
        assert!(html.contains(&format!("api?v=3.0&ak={BAIDU_MAP_AK}")));
        assert!(html.contains("referrerpolicy=\"no-referrer\""));
        assert!(html.contains("https://tile.openstreetmap.org/{z}/{x}/{y}.png"));
        assert!(!html.contains("<script src=\"https://unpkg.com/leaflet"));
        assert!(!html.contains("<link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet"));
    }

    #[test]
    fn imports_are_persistent_unique_and_only_copies_are_deleted() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("default.txt");
        fs::write(&source, DEFAULT_ROUTE).unwrap();
        assert_eq!(import(dir.path(), &source).unwrap(), "default_1");
        assert_eq!(import(dir.path(), &source).unwrap(), "default_2");
        let (routes, skipped) = list(dir.path()).unwrap();
        assert!(skipped.is_empty());
        assert_eq!(routes.len(), 3);
        assert!(delete(dir.path(), &routes[0]).is_err());
        let outside = Route {
            name: "outside".into(),
            path: Some(source.clone()),
            points: parse(DEFAULT_ROUTE).unwrap(),
        };
        assert!(delete(dir.path(), &outside).is_err());
        delete(dir.path(), &routes[1]).unwrap();
        assert_eq!(list(dir.path()).unwrap().0.len(), 2);
        assert!(source.exists());
    }

    #[test]
    fn one_broken_route_file_does_not_hide_the_others() {
        let dir = tempfile::tempdir().unwrap();
        let routes_dir = dir.path().join("routes");
        fs::create_dir_all(&routes_dir).unwrap();
        fs::write(routes_dir.join("good.txt"), DEFAULT_ROUTE).unwrap();
        fs::write(routes_dir.join("broken.txt"), "not a route").unwrap();
        let (routes, skipped) = list(dir.path()).unwrap();
        assert_eq!(
            routes.iter().map(|r| r.name.as_str()).collect::<Vec<_>>(),
            ["default", "good"]
        );
        assert_eq!(skipped.len(), 1);
        assert!(skipped[0].starts_with("broken.txt："));
    }

    #[test]
    fn oversized_invalid_and_empty_imports_do_not_create_routes() {
        let dir = tempfile::tempdir().unwrap();
        let source = dir.path().join("invalid.txt");
        for text in ["", "NaN,31\n121,31", "1,2,3\n4,5"] {
            fs::write(&source, text).unwrap();
            assert!(import(dir.path(), &source).is_err());
        }
        let file = fs::File::create(&source).unwrap();
        file.set_len(MAX_ROUTE_BYTES + 1).unwrap();
        assert!(read(&source).is_err());
        assert!(!dir.path().join("routes").exists());
    }

    #[test]
    fn closed_route_can_repeat_and_coordinate_calibration_is_preserved() {
        let points = parse("121,31\n121.001,31\n121.001,31.001\n121,31").unwrap();
        let sample = resample(&points, 2_000.0, 3.0).unwrap();
        assert!(sample.windows(2).all(|p| haversine(p[0], p[1]) < 3.01));
        let corrected = corrected(&points);
        assert!((corrected[0].lon - 120.99358128505265).abs() < 1e-10);
        assert!((corrected[0].lat - 30.99369111023523).abs() < 1e-10);
    }
}
