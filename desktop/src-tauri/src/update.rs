use semver::Version;
use serde_json::Value;
use std::time::Duration;

pub fn latest(items: &Value) -> Option<Version> {
    items
        .as_array()?
        .iter()
        .filter(|item| item["draft"] != true)
        .filter_map(|item| {
            Version::parse(item["tag_name"].as_str()?.trim_start_matches(['v', 'V'])).ok()
        })
        .max()
}

const RELEASES_API: &str =
    "https://api.github.com/repos/JackyTJie/SJTURunningMan_Advanced_Edition/releases?per_page=30";
const RELEASES_FEED: &str =
    "https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition/releases.atom";

fn latest_from_feed(feed: &str) -> Option<Version> {
    // Read entry IDs, never titles or release notes, which can mention other versions.
    let ids = regex::Regex::new(r"<id>tag:github\.com,2008:Repository/\d+/([^<]+)</id>").ok()?;
    ids.captures_iter(feed)
        .filter_map(|entry| Version::parse(entry[1].trim_start_matches(['v', 'V'])).ok())
        .max()
}

fn fetch_latest(
    client: &reqwest::blocking::Client,
    api_url: &str,
    feed_url: &str,
) -> Result<Version, String> {
    let api_result = (|| {
        let value: Value = client.get(api_url).send()?.error_for_status()?.json()?;
        Ok::<_, reqwest::Error>(latest(&value))
    })();
    if let Ok(Some(version)) = api_result {
        return Ok(version);
    }
    // The official public feed does not consume the REST API's anonymous quota.
    let feed = client
        .get(feed_url)
        .send()
        .and_then(reqwest::blocking::Response::error_for_status)
        .and_then(reqwest::blocking::Response::text)
        .map_err(|error| {
            format!(
                "暂时无法获取版本信息：{}；可前往 GitHub Releases 手动查看",
                crate::api::network_error(error)
            )
        })?;
    latest_from_feed(&feed).ok_or_else(|| "未找到可用版本，可前往 GitHub Releases 手动查看".into())
}

pub fn check(current: &str) -> Result<String, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(8))
        .user_agent(format!("SJTURunningMan/{current}"))
        .build()
        .map_err(crate::api::network_error)?;
    let remote = fetch_latest(&client, RELEASES_API, RELEASES_FEED)?;
    let local = Version::parse(current.trim_start_matches('v')).map_err(|_| "本地版本无效")?;
    Ok(if remote > local {
        format!("发现新版本 v{remote}，可前往 GitHub 的 Releases 下载")
    } else {
        format!("当前 v{local} 已是最新版本")
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn feed_selects_versions_from_entry_ids_only() {
        let feed = r#"<feed>
          <id>tag:github.com,2008:Repository/123/python-qtui-final</id>
          <id>tag:github.com,2008:Repository/123/v4.5.0-beta.4</id>
          <id>tag:github.com,2008:Repository/123/v4.5.0</id>
          <id>tag:github.com,2008:Repository/123/v4.4.0</id>
          <content>v99.0.0</content>
        </feed>"#;
        assert_eq!(
            latest_from_feed(feed),
            Some(Version::parse("4.5.0").unwrap())
        );
        assert!(latest_from_feed("<feed></feed>").is_none());
        assert_eq!(
            latest_from_feed("<id>tag:github.com,2008:Repository/123/v4.5.0-beta.4</id>"),
            Some(Version::parse("4.5.0-beta.4").unwrap())
        );
    }

    #[test]
    fn rate_limited_api_falls_back_to_official_feed() {
        use std::io::{Read, Write};
        for status in [403, 429] {
            let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
            let base = format!("http://{}", listener.local_addr().unwrap());
            let server = std::thread::spawn(move || {
                for (path, status, body) in [
                    ("/api", status, "rate limited"),
                    (
                        "/feed",
                        200,
                        "<id>tag:github.com,2008:Repository/123/v4.5.0-beta.4</id>",
                    ),
                ] {
                    let (mut stream, _) = listener.accept().unwrap();
                    stream
                        .set_read_timeout(Some(Duration::from_secs(5)))
                        .unwrap();
                    let mut request = Vec::new();
                    let mut buffer = [0; 1024];
                    while !request.ends_with(b"\r\n\r\n") {
                        let count = stream.read(&mut buffer).unwrap();
                        assert!(count > 0);
                        request.extend_from_slice(&buffer[..count]);
                    }
                    assert!(String::from_utf8_lossy(&request).starts_with(&format!("GET {path} ")));
                    write!(stream, "HTTP/1.1 {status} Mock\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).unwrap();
                }
            });
            let client = reqwest::blocking::Client::builder()
                .no_proxy()
                .timeout(Duration::from_secs(5))
                .build()
                .unwrap();
            let result = fetch_latest(&client, &format!("{base}/api"), &format!("{base}/feed"));
            server.join().unwrap();
            assert_eq!(result.unwrap(), Version::parse("4.5.0-beta.4").unwrap());
        }
    }

    #[test]
    fn release_selection_obeys_semver_and_skips_drafts() {
        let items = serde_json::json!([{"tag_name":"v4.5.0-beta.1"},{"tag_name":"v4.5.0"},{"tag_name":"v9.0.0","draft":true},{"tag_name":"invalid"}]);
        assert_eq!(latest(&items).unwrap(), Version::parse("4.5.0").unwrap());
        assert!(latest(&serde_json::json!([])).is_none());
    }
}
