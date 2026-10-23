use std::{
    collections::HashMap,
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    thread::{self, JoinHandle},
    time::Duration,
};

pub struct MapServer {
    address: SocketAddr,
    prefix: String,
    pages: Arc<Mutex<HashMap<String, String>>>,
    stopping: Arc<AtomicBool>,
    worker: Option<JoinHandle<()>>,
}

impl MapServer {
    pub fn start() -> Result<Self, String> {
        let listener = TcpListener::bind((std::net::Ipv4Addr::LOCALHOST, 0))
            .map_err(|_| "无法启动本机地图服务")?;
        let address = listener.local_addr().map_err(|_| "无法读取本机地图地址")?;
        let pages = Arc::new(Mutex::new(HashMap::new()));
        let stopping = Arc::new(AtomicBool::new(false));
        let prefix = format!("/{}", uuid::Uuid::new_v4());
        let worker_pages = pages.clone();
        let worker_stopping = stopping.clone();
        let worker_prefix = prefix.clone();
        let worker = thread::Builder::new()
            .name("local-maps".into())
            .spawn(move || loop {
                match listener.accept() {
                    Ok((mut stream, _)) => {
                        if worker_stopping.load(Ordering::Relaxed) {
                            break;
                        }
                        let _ = serve(&mut stream, address, &worker_prefix, &worker_pages);
                    }
                    Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                    Err(_) => break,
                }
            })
            .map_err(|_| "无法启动本机地图服务线程")?;
        Ok(Self {
            address,
            prefix,
            pages,
            stopping,
            worker: Some(worker),
        })
    }

    pub fn publish(&self, name: &str, html: String) -> Result<String, String> {
        if !["preview", "planner"].contains(&name) {
            return Err("未知地图页面".into());
        }
        self.pages
            .lock()
            .map_err(|_| "无法更新地图页面")?
            .insert(name.into(), html);
        Ok(format!("http://{}{}/{}", self.address, self.prefix, name))
    }
}

impl Drop for MapServer {
    fn drop(&mut self) {
        self.stopping.store(true, Ordering::Relaxed);
        // 唤醒阻塞的 accept，服务空闲时不轮询。
        let _ = TcpStream::connect_timeout(&self.address, Duration::from_millis(500));
        if let Some(worker) = self.worker.take() {
            let _ = worker.join();
        }
    }
}

fn serve(
    stream: &mut TcpStream,
    address: SocketAddr,
    prefix: &str,
    pages: &Mutex<HashMap<String, String>>,
) -> std::io::Result<()> {
    stream.set_read_timeout(Some(Duration::from_millis(500)))?;
    stream.set_write_timeout(Some(Duration::from_millis(500)))?;
    let mut request = Vec::new();
    let mut buffer = [0; 1024];
    while !request.windows(4).any(|part| part == b"\r\n\r\n") {
        let count = stream.read(&mut buffer)?;
        if count == 0 {
            return Ok(());
        }
        request.extend_from_slice(&buffer[..count]);
        if request.len() > 8192 {
            return respond(stream, 431, "Request too large", false, None);
        }
    }
    let Ok(request) = std::str::from_utf8(&request) else {
        return respond(stream, 400, "Invalid request", false, None);
    };
    let mut lines = request.split("\r\n");
    let parts: Vec<_> = lines
        .next()
        .unwrap_or_default()
        .split_whitespace()
        .collect();
    if parts.len() != 3 {
        return respond(stream, 400, "Invalid request", false, None);
    }
    let head = parts[0] == "HEAD";
    if parts[0] != "GET" && !head {
        return respond(stream, 405, "Method not allowed", false, None);
    }
    // 只接受真实本机来源，不提供任意文件访问或跨站读取。
    let host = lines.find_map(|line| {
        let (key, value) = line.split_once(':')?;
        key.eq_ignore_ascii_case("host").then_some(value.trim())
    });
    if host != Some(address.to_string().as_str()) {
        return respond(stream, 403, "Forbidden", head, None);
    }
    let page = parts[1]
        .strip_prefix(prefix)
        .and_then(|path| path.strip_prefix('/'))
        .and_then(|name| {
            pages
                .lock()
                .ok()?
                .get(name)
                .cloned()
                .map(|html| (name.to_string(), html))
        });
    match page {
        // 只有预览页会被应用以 iframe 嵌入；规划器仍在独立浏览器窗口中打开。
        Some((name, html)) => respond(stream, 200, &html, head, Some(name.as_str())),
        None => respond(stream, 404, "Not found", head, None),
    }
}

/// 预览页只加载 Leaflet 与 OpenStreetMap 瓦片，因此不需要百度域名或 'unsafe-eval'。
const OSM_CONTENT_SECURITY_POLICY: &str = "default-src 'none'; \
script-src 'unsafe-inline' https://unpkg.com; \
style-src 'unsafe-inline' https://unpkg.com; \
img-src 'self' data: https://unpkg.com https://tile.openstreetmap.org; \
font-src https://unpkg.com; \
base-uri 'none'; form-action 'none'";

/// 规划器仍默认百度、可切 OpenStreetMap。百度 BMap 会继续加载 bdimg / bdstatic
/// 下的脚本、样式、图片和瓦片，并在初始化时使用 eval，因此需要额外放行
/// 'unsafe-eval' 与百度域名；表单提交和跨站读取仍保持关闭。
const PLANNER_CONTENT_SECURITY_POLICY: &str = "default-src 'none'; \
script-src 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://api.map.baidu.com https://*.baidu.com \
https://*.bdimg.com https://*.bdstatic.com http://api.map.baidu.com http://*.baidu.com \
http://*.bdimg.com http://*.bdstatic.com; \
style-src 'unsafe-inline' https://unpkg.com https://api.map.baidu.com https://*.baidu.com \
https://*.bdimg.com https://*.bdstatic.com; \
img-src 'self' data: https://unpkg.com https://tile.openstreetmap.org https://api.map.baidu.com \
https://*.baidu.com https://*.bdimg.com https://*.bdstatic.com http://*.baidu.com \
http://*.bdimg.com http://*.bdstatic.com; \
font-src https://unpkg.com https://api.map.baidu.com https://*.baidu.com https://*.bdimg.com \
https://*.bdstatic.com; \
connect-src https://api.map.baidu.com https://*.baidu.com https://*.bdimg.com \
https://*.bdstatic.com http://api.map.baidu.com http://*.baidu.com http://*.bdimg.com \
http://*.bdstatic.com; \
base-uri 'none'; form-action 'none'";

/// 预览页要嵌进应用 WebView。Windows 上是 http(s)://tauri.localhost，其余平台
/// 是 tauri://localhost，开发时是 Vite 的 localhost:1420；除此之外不允许被框。
const PREVIEW_FRAME_ANCESTORS: &str = "'self' tauri://localhost http://tauri.localhost \
https://tauri.localhost http://localhost:1420";

fn content_security_policy(name: Option<&str>) -> String {
    match name {
        Some("preview") => {
            format!("{OSM_CONTENT_SECURITY_POLICY}; frame-ancestors {PREVIEW_FRAME_ANCESTORS}")
        }
        Some(_) => format!("{PLANNER_CONTENT_SECURITY_POLICY}; frame-ancestors 'none'"),
        None => format!("{OSM_CONTENT_SECURITY_POLICY}; frame-ancestors 'none'"),
    }
}

fn respond(
    stream: &mut TcpStream,
    status: u16,
    body: &str,
    head: bool,
    page: Option<&str>,
) -> std::io::Result<()> {
    let csp = content_security_policy(page);
    write!(stream, "HTTP/1.1 {status} {}\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nReferrer-Policy: strict-origin-when-cross-origin\r\nContent-Security-Policy: {csp}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n", if status == 200 {"OK"} else {"Error"}, body.len())?;
    if !head {
        stream.write_all(body.as_bytes())?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(server: &MapServer, method: &str, path: &str, host: &str) -> String {
        let mut stream = TcpStream::connect(server.address).unwrap();
        stream
            .set_read_timeout(Some(Duration::from_secs(2)))
            .unwrap();
        write!(
            stream,
            "{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        )
        .unwrap();
        let mut response = String::new();
        stream.read_to_string(&mut response).unwrap();
        response
    }

    #[test]
    fn pages_have_http_origin_and_referrer_without_disk_or_cross_origin_access() {
        let server = MapServer::start().unwrap();
        let url = server
            .publish("planner", "<html>规划</html>".into())
            .unwrap();
        let url = reqwest::Url::parse(&url).unwrap();
        assert_eq!(url.host_str(), Some("127.0.0.1"));
        let host = server.address.to_string();
        let response = request(&server, "GET", url.path(), &host);
        assert!(response.starts_with("HTTP/1.1 200"));
        assert!(response.contains("Referrer-Policy: strict-origin-when-cross-origin\r\n"));
        assert!(response.contains("Content-Security-Policy: default-src 'none';"));
        assert!(response.contains("script-src 'unsafe-inline' 'unsafe-eval'"));
        assert!(response.contains("https://api.map.baidu.com"));
        assert!(response.contains("https://*.bdimg.com"));
        assert!(response.contains("https://*.bdstatic.com"));
        assert!(response.contains("connect-src https://api.map.baidu.com"));
        assert!(!response.contains("connect-src 'none'"));
        assert!(response.contains("base-uri 'none'"));
        assert!(response.contains("form-action 'none'"));
        assert!(response.contains("frame-ancestors 'none'"));
        assert!(!response.contains("Access-Control-Allow-Origin"));
        assert!(response.ends_with("<html>规划</html>"));
        assert!(request(&server, "GET", url.path(), "outside.invalid").starts_with("HTTP/1.1 403"));
        for path in ["/", "/preview", "/../settings.json", "/route-preview.html"] {
            assert!(request(&server, "GET", path, &host).starts_with("HTTP/1.1 404"));
        }
        assert!(server
            .publish("../settings.json", "private".into())
            .is_err());
    }

    #[test]
    fn preview_page_uses_osm_only_and_can_only_be_framed_by_the_app() {
        let server = MapServer::start().unwrap();
        let url = server
            .publish("preview", "<html>路线</html>".into())
            .unwrap();
        let url = reqwest::Url::parse(&url).unwrap();
        let host = server.address.to_string();
        let response = request(&server, "GET", url.path(), &host);
        assert!(response.starts_with("HTTP/1.1 200"));
        assert!(response.contains("Content-Security-Policy: default-src 'none';"));
        assert!(response.contains("https://unpkg.com"));
        assert!(response.contains("https://tile.openstreetmap.org"));
        assert!(!response.contains("api.map.baidu.com"));
        assert!(!response.contains("bdimg.com"));
        assert!(!response.contains("'unsafe-eval'"));
        assert!(response.contains("frame-ancestors 'self' tauri://localhost"));
        for origin in [
            "http://tauri.localhost",
            "https://tauri.localhost",
            "http://localhost:1420",
        ] {
            assert!(response.contains(origin), "frame-ancestors 缺少 {origin}");
        }
        assert!(!response.contains("frame-ancestors 'none'"));

        // 未知页面仍按最严格的策略返回，避免把 404 变成可嵌入的探测面。
        let missing = format!("{}-missing", url.path());
        let response = request(&server, "GET", &missing, &host);
        assert!(response.starts_with("HTTP/1.1 404"));
        assert!(response.contains("frame-ancestors 'none'"));
    }

    #[test]
    fn pages_can_be_updated_and_server_closes_with_app() {
        let server = MapServer::start().unwrap();
        let url = reqwest::Url::parse(&server.publish("planner", "old".into()).unwrap()).unwrap();
        server.publish("planner", "new".into()).unwrap();
        let host = server.address.to_string();
        assert!(request(&server, "GET", url.path(), &host).ends_with("new"));
        let head = request(&server, "HEAD", url.path(), &host);
        assert!(head.starts_with("HTTP/1.1 200"));
        assert!(head.ends_with("\r\n\r\n"));
        assert!(request(&server, "POST", url.path(), &host).starts_with("HTTP/1.1 405"));
        let address = server.address;
        drop(server);
        assert!(TcpStream::connect(address).is_err());
    }
}
