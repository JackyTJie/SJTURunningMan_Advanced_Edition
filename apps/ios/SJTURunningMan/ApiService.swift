//
//  ApiService.swift
//  SJTURunningMan
//
//  与安卓版 / 电脑版保持一致的接口封装（UID、打卡规则、上传）。
//

import Foundation
import WebKit  // 需要用来访问 WKWebsiteDataStore

final class ApiService {

    // MARK: - User Agent / 常量

    static let appUserAgent =
        "Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Version/4.0 Chrome/138.0.7204.67 Safari/537.36 TaskCenterApp/3.5.0"
    static let webUserAgent =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    static let taskCenterPackage = "edu.sjtu.infoplus.taskcenter"

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.httpCookieStorage = HTTPCookieStorage.shared
        config.httpShouldSetCookies = true
        config.timeoutIntervalForRequest = 20
        config.timeoutIntervalForResource = 30
        return URLSession(configuration: config)
    }()

    // MARK: - Cookie 工具

    /// 同步 WebView 的 cookie 到 HTTPCookieStorage
    static func syncCookiesFromWebView(completion: @escaping () -> Void) {
        let cookieStore = WKWebsiteDataStore.default().httpCookieStore
        cookieStore.getAllCookies { cookies in
            for cookie in cookies {
                HTTPCookieStorage.shared.setCookie(cookie)
            }
            completion()
        }
    }

    /// 清除所有 cookie
    func clearCookies() {
        HTTPCookieStorage.shared.removeCookies(since: Date.distantPast)
    }

    /// 仅精准匹配 jAccount 登录页特征，避免把正常响应误判为登录页。
    private func isJAccountLoginPage(_ content: String) -> Bool {
        content.contains("Login jAccount") ||
        content.contains("jaccount.sjtu.edu.cn") ||
        content.contains("扫码登录") ||
        content.contains("Scan QR code") ||
        content.contains("统一身份认证")
    }

    private func looksLikeUid(_ text: String) -> Bool {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.range(of: "^[a-zA-Z0-9_-]{4,}$", options: .regularExpression) != nil
    }

    // MARK: - 获取 UID

    func getUid() async -> String? {
        guard let url = URL(string: AppConfig.uidURL) else { return nil }
        var request = URLRequest(url: url)
        request.setValue(Self.appUserAgent, forHTTPHeaderField: "User-Agent")
        request.setValue("application/json, text/plain, */*", forHTTPHeaderField: "Accept")
        request.setValue(Self.taskCenterPackage, forHTTPHeaderField: "X-Requested-With")
        request.setValue("https://\(AppConfig.host)/phone/", forHTTPHeaderField: "Referer")

        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else { return nil }
            let body = String(data: data, encoding: .utf8) ?? ""

            if isJAccountLoginPage(body) || httpResponse.statusCode == 302 || httpResponse.statusCode == 403 {
                return nil
            }

            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                let code = (json["code"] as? NSNumber)?.doubleValue
                let uid = (json["data"] as? [String: Any])?["uid"] as? String
                if code != 0 || uid == nil || uid!.isEmpty {
                    return nil
                }
                return uid
            }

            // 可能是纯文本 / JSON 字符串形式的 uid
            let trimmed = body.trimmingCharacters(in: .whitespacesAndNewlines)
            return looksLikeUid(trimmed) ? trimmed : nil
        } catch {
            print("获取 UID 失败: \(error)")
            return nil
        }
    }

    // MARK: - 打卡规则

    /// 拉取跑步打卡规则（配速上下限、run id），失败时返回默认规则。
    func getPointRules(authToken: String, longitude: Double, latitude: Double) async -> PointRules {
        let fallback = PointRules.default

        // 预热一次个人数据接口，失败不影响后续
        if let warmURL = URL(string: AppConfig.myDataURL) {
            var warm = URLRequest(url: warmURL)
            warm.setValue(Self.appUserAgent, forHTTPHeaderField: "User-Agent")
            warm.setValue("application/json, text/plain, */*", forHTTPHeaderField: "Accept")
            warm.setValue(authToken, forHTTPHeaderField: "Authorization")
            _ = try? await session.data(for: warm)
        }

        let locationValue = String(format: "%.14f,%.14f", longitude, latitude)
        var components = URLComponents(string: AppConfig.pointRuleURL)
        components?.queryItems = [URLQueryItem(name: "location", value: locationValue)]
        guard let url = components?.url else { return fallback }

        var request = URLRequest(url: url)
        request.setValue(Self.webUserAgent, forHTTPHeaderField: "User-Agent")
        request.setValue("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", forHTTPHeaderField: "Accept")
        request.setValue(authToken, forHTTPHeaderField: "Authorization")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        request.setValue(url.absoluteString, forHTTPHeaderField: "Referer")

        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
                return fallback
            }
            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let ruleData = json["data"] as? [String: Any],
                  let rules = ruleData["rules"] as? [String: Any] else {
                return fallback
            }
            let id = (rules["id"] as? NSNumber)?.intValue ?? 6
            let spmin = (rules["spmin"] as? NSNumber)?.intValue ?? 180
            let spmax = (rules["spmax"] as? NSNumber)?.intValue ?? 540
            return PointRules(id: id == 6 ? 9 : id, spmin: spmin, spmax: spmax)
        } catch {
            print("getPointRules 失败，使用默认规则: \(error)")
            return fallback
        }
    }

    // MARK: - 上传

    func upload(authToken: String, payload: [[String: Any]]) async -> (success: Bool, message: String, needRelogin: Bool) {
        guard let url = URL(string: AppConfig.uploadURL) else {
            return (false, "URL error", false)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue(authToken, forHTTPHeaderField: "Authorization")
        request.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.setValue("gzip", forHTTPHeaderField: "Accept-Encoding")
        request.setValue("okhttp/4.10.0", forHTTPHeaderField: "User-Agent")

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])
        } catch {
            return (false, "Payload serialization error", false)
        }

        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                return (false, "No response", false)
            }
            let body = String(data: data, encoding: .utf8) ?? ""

            if isJAccountLoginPage(body) || httpResponse.statusCode == 403 || httpResponse.statusCode == 401 {
                return (false, "cookie已过期，需要重新登录", true)
            }

            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let code = (json["code"] as? NSNumber)?.intValue, code == 0 {
                return (true, json["message"] as? String ?? "成功", false)
            }
            return (false, String(body.prefix(200)), false)
        } catch {
            return (false, "网络错误: \(error.localizedDescription)", false)
        }
    }

    // MARK: - 学期统计

    /// 只读学期统计：达标公里、完成率、学期起止与本学期打卡日期。
    ///
    /// 这些接口只要 pe.sjtu.edu.cn 的会话 Cookie，不需要 `/sports/my/uid` 换的 token。
    /// 其中学期目标与学期起止日期失败时不阻塞其余数据。
    func semesterStats() async throws -> SemesterStats {
        let summary = firstObject(try await getJson(AppConfig.myDataURL, [:], "学期统计"), "data")
        let resultKm = jsonNumber(summary?["resultKm"])
        let totalKm = jsonNumber(summary?["totalKm"])
        let percent = jsonNumber(summary?["percent"]) ?? percentFromRatio(resultKm, totalKm)

        let targetKm = try await optionalStats {
            try jsonNumber(objOf(await self.getJson(AppConfig.semesterTargetURL, [:], "学期目标"), "data")?["target"])
        }

        let entry = firstObject(
            try await getJson(AppConfig.semesterListURL, ["type": "1"], "学期列表"), "data")
        guard let semesterId = stringOrNull(entry, "semesterId")?.trimmingCharacters(in: .whitespaces),
              !semesterId.isEmpty else {
            throw StatsError(message: "学期列表缺少 semesterId")
        }
        let semesterName = stringOrNull(entry, "semesterName")?.trimmingCharacters(in: .whitespaces).nilIfEmpty
            ?? "本学期"

        let range = try await optionalStats {
            let item = firstObject(
                objOf(try await self.postEmptyJson(AppConfig.userInfoURL, "学期日期"), "data"),
                "semesterDateList"
            )
            let start = serverDate(stringOrNull(item, "startDate"))
            let end = serverDate(stringOrNull(item, "endDate"))
            if let start, let end {
                return SemesterRange.of(start: start, end: end)
            }
            return nil
        }

        let records = try await getJson(
            AppConfig.resultListURL,
            ["selectId": semesterId, "type": "1"],
            "跑步记录"
        )
        var runDays: [Date: DayState] = [:]
        for week in arrOf(records, "data") {
            guard let weekObject = week as? [String: Any] else { continue }
            for detail in arrOf(weekObject, "details") {
                guard let record = detail as? [String: Any],
                      let date = serverDate(stringOrNull(record, "timeFrom")) else { continue }
                let state: DayState = countsTowardScore(record["state"]) ? .valid : .invalid
                recordDay(&runDays, date, state)
            }
        }

        return SemesterStats(
            resultKm: resultKm,
            totalKm: totalKm,
            percent: percent,
            targetKm: targetKm,
            semesterName: semesterName,
            range: range,
            runDays: runDays
        )
    }

    private func getJson(_ urlString: String, _ query: [String: String], _ what: String) async throws -> [String: Any] {
        let request = try makeStatsRequest(urlString, query, what)
        return try await sendStats(request, what)
    }

    private func postEmptyJson(_ urlString: String, _ what: String) async throws -> [String: Any] {
        var request = try makeStatsRequest(urlString, [:], what)
        request.httpMethod = "POST"
        request.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("{}".utf8)
        return try await sendStats(request, what)
    }

    private func makeStatsRequest(_ urlString: String, _ query: [String: String], _ what: String) throws -> URLRequest {
        guard var components = URLComponents(string: urlString) else {
            throw StatsError(message: "\(what)：地址无效")
        }
        if !query.isEmpty {
            components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components.url else { throw StatsError(message: "\(what)：地址无效") }

        var request = URLRequest(url: url)
        request.setValue(Self.appUserAgent, forHTTPHeaderField: "User-Agent")
        request.setValue("application/json, text/plain, */*", forHTTPHeaderField: "Accept")
        request.setValue("https://\(AppConfig.host)/phone/", forHTTPHeaderField: "Referer")
        return request
    }

    private func sendStats(_ request: URLRequest, _ what: String) async throws -> [String: Any] {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw SessionExpiredError(message: "\(what)：\(Self.loginExpired)")
        }
        // 未登录时这些接口会跳到登录页，跟随后拿到的是 HTML；
        // 统一识别成「登录状态已过期」，并且绝不把响应正文带进错误信息。
        let finalURL = http.url?.absoluteString ?? ""
        if finalURL.contains("/login") || finalURL.contains("jaccount") {
            throw SessionExpiredError(message: "\(what)：\(Self.loginExpired)")
        }
        guard (200..<300).contains(http.statusCode) else {
            print("\(what): HTTP \(http.statusCode)")
            throw StatsError(message: "\(what)：服务器返回 HTTP \(http.statusCode)")
        }
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            print("\(what): 响应不是可用的 JSON")
            throw SessionExpiredError(message: "\(what)：\(Self.loginExpired)")
        }
        if let code = json["code"], !isZeroCode(code) {
            print("\(what): code 非 0")
            throw SessionExpiredError(message: "\(what)：\(Self.loginExpired)")
        }
        return json
    }

    private func isZeroCode(_ value: Any) -> Bool {
        switch value {
        case let number as NSNumber: return number.doubleValue == 0
        case let string as String:
            let trimmed = string.trimmingCharacters(in: .whitespaces)
            return trimmed == "0" || (Double(trimmed) ?? 1) == 0
        default: return false
        }
    }

    /// 服务器的数值都是字符串（"80.00"、"100.00"、"80"），偶尔带百分号或千分位。
    private func jsonNumber(_ value: Any?) -> Double? {
        let raw: String
        switch value {
        case let number as NSNumber: raw = number.stringValue
        case let string as String: raw = string
        default: return nil
        }
        var text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.hasSuffix("%") { text.removeLast() }
        text = text.replacingOccurrences(of: ",", with: "")
        guard let parsed = Double(text), parsed.isFinite else { return nil }
        return parsed
    }

    /// 服务器日期形如 `2026-09-19 07:52:19`，只取前 10 个字符；解析不出的记录直接跳过。
    private func serverDate(_ text: String?) -> Date? {
        guard let text, text.count >= 10 else { return nil }
        return Self.dayFormatter.date(from: String(text.prefix(10)))
    }

    /// `state == "0"` 计入成绩，12/13 等是无效记录。
    private func countsTowardScore(_ value: Any?) -> Bool {
        switch value {
        case let number as NSNumber: return number.intValue == 0
        case let string as String: return Int(string.trimmingCharacters(in: .whitespaces)) == 0
        default: return false
        }
    }

    private func objOf(_ parent: [String: Any]?, _ key: String) -> [String: Any]? {
        parent?[key] as? [String: Any]
    }

    private func arrOf(_ parent: [String: Any]?, _ key: String) -> [Any] {
        (parent?[key] as? [Any]) ?? []
    }

    private func firstObject(_ parent: [String: Any]?, _ key: String) -> [String: Any]? {
        arrOf(parent, key).first as? [String: Any]
    }

    private func stringOrNull(_ object: [String: Any]?, _ key: String) -> String? {
        object?[key] as? String
    }

    /// 非阻塞步骤：失败只说明「这一步没有数据」，但任务取消必须照常传播。
    private func optionalStats<T>(_ block: () async throws -> T?) async throws -> T? {
        do {
            return try await block()
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            return nil
        }
    }

    private static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = CST.calendar
        formatter.timeZone = CST.calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private static let loginExpired = "登录状态已过期，请重新登录后重试"
}

// MARK: - 学期统计的错误类型

protocol StatsFailure: Error {
    var message: String { get }
}

struct StatsError: StatsFailure {
    let message: String
}

struct SessionExpiredError: StatsFailure {
    let message: String
}

private extension String {
    var nilIfEmpty: String? { isEmpty ? nil : self }
}
