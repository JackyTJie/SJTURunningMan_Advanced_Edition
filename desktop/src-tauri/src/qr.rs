//! jAccount 扫码登录的通道层。
//!
//! 学校登录页用 WebSocket 订阅 `/jaccount/sub/<uuid>`：客户端先要一张二维码票据
//! （`ts` + `sig`），服务端在手机确认后推送 `LOGIN`。这里只做「连接、取票、读消息」，
//! 会话、图片校验与 OAuth 收尾仍在 `api` 模块，便于离线测试与复用。

use std::{
    net::TcpStream,
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};
use tungstenite::{
    client::IntoClientRequest,
    http::{
        header::{HeaderValue, COOKIE, ORIGIN},
        Request,
    },
    stream::MaybeTlsStream,
    Message, WebSocket,
};

/// 学校页面每 60 秒换一张二维码；这里与它保持一致。
pub const REFRESH_INTERVAL: Duration = Duration::from_secs(60);

/// 读超时只用来定期检查取消标记；tungstenite 会把未读完的帧留在缓冲区里，
/// 超时后的下一次读取可以接着解析。
const READ_TIMEOUT: Duration = Duration::from_millis(500);

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Ticket {
    pub ts: u64,
    pub sig: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Signal {
    /// 服务端下发了一张新的二维码票据。
    Ticket(Ticket),
    /// 手机已确认登录，可以访问 `expresslogin` 收尾。
    Login,
    /// 与登录无关的消息（心跳、错误提示等），忽略。
    Other,
}

pub struct Channel {
    socket: WebSocket<MaybeTlsStream<TcpStream>>,
}

impl Channel {
    /// `cookie` 是学校登录会话的 Cookie 头；浏览器打开二维码通道时同样会发送它。
    pub fn open_with_cookie(base: &str, uuid: &str, cookie: &str) -> Result<Self, String> {
        let request = subscription_request(base, uuid, cookie)?;
        let (mut socket, _) =
            tungstenite::connect(request).map_err(|_| "二维码通道连接失败，请重试")?;
        set_read_timeout(&mut socket)?;
        let mut channel = Self { socket };
        channel.request()?;
        Ok(channel)
    }

    /// 请服务端再下发一张票据。学校页面在打开与每隔一分钟时各发一次。
    pub fn request(&mut self) -> Result<(), String> {
        self.socket
            .send(Message::text("{ \"type\": \"UPDATE_QR_CODE\" }"))
            .map_err(|_| "二维码通道不可用，请重新获取".to_string())
    }

    /// 读一条消息；`None` 表示本次读超时，调用方可以继续循环。
    pub fn poll_signal(&mut self) -> Result<Option<Signal>, String> {
        loop {
            match self.socket.read() {
                Ok(Message::Text(text)) => return Ok(parse(&text)),
                Ok(Message::Binary(_))
                | Ok(Message::Ping(_))
                | Ok(Message::Pong(_))
                | Ok(Message::Frame(_)) => continue,
                Ok(Message::Close(_)) => return Err("二维码通道已关闭，请重新获取".into()),
                Err(tungstenite::Error::Io(error))
                    if matches!(
                        error.kind(),
                        std::io::ErrorKind::WouldBlock | std::io::ErrorKind::TimedOut
                    ) =>
                {
                    return Ok(None)
                }
                Err(tungstenite::Error::ConnectionClosed) => {
                    return Err("二维码通道已关闭，请重新获取".into())
                }
                Err(_) => return Err("二维码通道异常，请重新获取".into()),
            }
        }
    }

    /// 等到下一张票据；期间持续检查取消标记，取消后立即返回。
    pub fn wait_ticket(&mut self, cancel: &AtomicBool) -> Result<Ticket, String> {
        loop {
            if cancel.load(Ordering::Relaxed) {
                return Err("二维码登录已取消".into());
            }
            if let Some(Signal::Ticket(ticket)) = self.poll_signal()? {
                return Ok(ticket);
            }
        }
    }

    pub fn close(&mut self) {
        let _ = self.socket.close(None);
        let _ = self.socket.flush();
    }
}

#[allow(unreachable_patterns)]
fn set_read_timeout(socket: &mut WebSocket<MaybeTlsStream<TcpStream>>) -> Result<(), String> {
    let result = match socket.get_mut() {
        MaybeTlsStream::Plain(stream) => stream.set_read_timeout(Some(READ_TIMEOUT)),
        MaybeTlsStream::Rustls(stream) => stream.get_ref().set_read_timeout(Some(READ_TIMEOUT)),
        // 只有启用 native-tls 才会出现其他分支；本项目的依赖组合里不会走到这里。
        _ => Ok(()),
    };
    result.map_err(|_| "二维码通道初始化失败".to_string())
}

/// 只接受十六进制与短横线组成的 uuid，避免把页面内容拼进 URL。
fn subscription_url(base: &str, uuid: &str) -> Result<String, String> {
    if uuid.is_empty()
        || uuid.len() > 64
        || !uuid
            .chars()
            .all(|value| value.is_ascii_hexdigit() || value == '-')
    {
        return Err("登录页面缺少二维码信息".into());
    }
    let base = base.trim_end_matches('/');
    let base = if let Some(rest) = base.strip_prefix("https://") {
        format!("wss://{rest}")
    } else if let Some(rest) = base.strip_prefix("http://") {
        format!("ws://{rest}")
    } else {
        return Err("登录地址无效".into());
    };
    Ok(format!("{base}/jaccount/sub/{uuid}"))
}

/// 按浏览器的习惯构造订阅请求：带会话 Cookie 与来源页，便于服务端把二维码
/// 与当前登录会话关联起来。
fn subscription_request(base: &str, uuid: &str, cookie: &str) -> Result<Request<()>, String> {
    let url = subscription_url(base, uuid)?;
    let mut request = url
        .as_str()
        .into_client_request()
        .map_err(|_| "二维码通道地址无效".to_string())?;
    let headers = request.headers_mut();
    if !cookie.is_empty() {
        let value = HeaderValue::from_str(cookie).map_err(|_| "二维码通道会话无效".to_string())?;
        headers.insert(COOKIE, value);
    }
    let origin = base.trim_end_matches('/').to_owned();
    if let Ok(value) = HeaderValue::from_str(&origin) {
        headers.insert(ORIGIN, value);
    }
    Ok(request)
}

/// 学校只下发 JSON 文本消息；无法识别的消息一律忽略。
pub fn parse(text: &str) -> Option<Signal> {
    let value: serde_json::Value = serde_json::from_str(text).ok()?;
    match value["type"].as_str()? {
        "LOGIN" => Some(Signal::Login),
        "UPDATE_QR_CODE" => {
            let payload = &value["payload"];
            let ts = payload["ts"]
                .as_u64()
                .or_else(|| payload["ts"].as_str().and_then(|text| text.parse().ok()))?;
            let sig = payload["sig"].as_str()?.trim();
            if sig.is_empty()
                || sig.len() > 128
                || !sig.chars().all(|value| value.is_ascii_alphanumeric())
            {
                return None;
            }
            Some(Signal::Ticket(Ticket {
                ts,
                sig: sig.to_owned(),
            }))
        }
        _ => Some(Signal::Other),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_wss_endpoint_from_the_login_base() {
        assert_eq!(
            subscription_url("https://jaccount.sjtu.edu.cn", "ab-12").unwrap(),
            "wss://jaccount.sjtu.edu.cn/jaccount/sub/ab-12"
        );
        assert_eq!(
            subscription_url("http://127.0.0.1:8080/", "ab12").unwrap(),
            "ws://127.0.0.1:8080/jaccount/sub/ab12"
        );
        assert!(subscription_url("https://jaccount.sjtu.edu.cn", "../admin").is_err());
        assert!(subscription_url("file:///etc/passwd", "ab12").is_err());
    }

    #[test]
    fn subscription_request_carries_session_and_origin() {
        let request = subscription_request(
            "https://jaccount.sjtu.edu.cn",
            "ab-12",
            "JSESSIONID=offline-test-only",
        )
        .unwrap();
        assert_eq!(
            request.uri().to_string(),
            "wss://jaccount.sjtu.edu.cn/jaccount/sub/ab-12"
        );
        assert_eq!(
            request.headers().get(COOKIE).unwrap(),
            "JSESSIONID=offline-test-only"
        );
        assert_eq!(
            request.headers().get(ORIGIN).unwrap(),
            "https://jaccount.sjtu.edu.cn"
        );
        let anonymous = subscription_request("https://jaccount.sjtu.edu.cn", "ab-12", "").unwrap();
        assert!(anonymous.headers().get(COOKIE).is_none());
        assert!(subscription_request("https://jaccount.sjtu.edu.cn", "../x", "").is_err());
    }

    #[test]
    fn parses_ticket_and_login_messages() {
        assert_eq!(
            parse(
                r#"{"type":"UPDATE_QR_CODE","error":0,"payload":{"sig":"8db6f42004a555","ts":1793021453379}}"#
            ),
            Some(Signal::Ticket(Ticket {
                ts: 1793021453379,
                sig: "8db6f42004a555".into(),
            }))
        );
        assert_eq!(parse(r#"{"type":"LOGIN"}"#), Some(Signal::Login));
        assert_eq!(
            parse(r#"{"type":"ERROR_MESSAGE","payload":"opaque"}"#),
            Some(Signal::Other)
        );
        assert_eq!(parse("not json"), None);
        assert_eq!(parse(r#"{"type":"UPDATE_QR_CODE","payload":{}}"#), None);
        assert_eq!(
            parse(r#"{"type":"UPDATE_QR_CODE","payload":{"sig":"a/b","ts":1}}"#),
            None
        );
    }
}
