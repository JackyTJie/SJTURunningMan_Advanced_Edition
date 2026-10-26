import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { PayloadItem } from '../model/PayloadModels';
import { UploadResult } from '../model/PayloadModels';
import { CookieService } from './CookieService';
import { PointRules } from '../viewmodel/TaskModels';
import { AppConfig } from '../config/AppConfig';
import { DayState, SemesterRange, SemesterStats, percentFromRatio, recordDay } from './SemesterStats';
import { parseDate } from '../utils/FormatUtil';

/**
 * 网络服务
 * 迁移自 Android: com.sjtu.runner.network.ApiService（OkHttp + WebViewCookieJar -> @ohos.net.http + WebCookieManager）
 * 差异：ArkTS 无 OkHttp CookieJar，Cookie 显式从 webview.WebCookieManager 读取并写入请求头。
 */
export class ApiService {
  private static readonly TAG: string = 'ApiService';

  /** 任务中心内嵌 WebView 的 UA（Android APP_USER_AGENT 原样） */
  private static readonly APP_USER_AGENT: string =
    'Mozilla/5.0 (Linux; Android 12; SM-S9080 Build/V417IR; wv) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Version/4.0 Chrome/138.0.7204.67 Safari/537.36 TaskCenterApp/3.5.0';

  /** 桌面浏览器 UA（Android WEB_USER_AGENT 原样） */
  private static readonly WEB_USER_AGENT: string =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36';

  /** 默认跑步规则（等价 Android PointRules(id = 9, spmin = 180, spmax = 540)） */
  private static readonly DEFAULT_POINT_RULES: PointRules = new PointRules(9, 180, 540);

  /** 精准判断是否为 jAccount 登录页（仅登录页才触发重新登录），逻辑与 Android 版一致 */
  private static isJAccountLoginPage(content: string): boolean {
    return content.includes('Login jAccount') ||
      content.includes('jaccount.sjtu.edu.cn') ||
      content.includes('扫码登录') ||
      content.includes('Scan QR code') ||
      content.includes('统一身份认证');
  }

  /**
   * UID 形态校验：等价 Android ApiService.looksLikeUid()
   * find(Regex("[a-zA-Z0-9_-]{4,}")) —— 至少 4 位，允许字母、数字、下划线与连字符。
   * （旧实现为 /^[a-zA-Z0-9]+$/，会接受 1-3 位假 UID、拒绝含 _ / - 的真实 UID，
   *   与 Android 行为相反，2026-10 评审 M3 修正。）
   */
  private static looksLikeUid(text: string): boolean {
    return /[a-zA-Z0-9_-]{4,}/.test(text);
  }

  /** 判断 JSON 值是否等价于 Kotlin map["code"] == 0.0 */
  private static isCodeZero(code: Object | undefined): boolean {
    if (typeof code === 'number') {
      return (code as number) === 0;
    }
    if (typeof code === 'string') {
      return (code as string) === '0';
    }
    return false;
  }

  /**
   * 获取 UID
   * 迁移自 ApiService.getUid(): 依次尝试
   * 1) JSON 对象 {code:0, data:{uid}}
   * 2) JSON 字符串（纯字母数字）
   * 3) 纯文本（纯字母数字）
   */
  async getUid(): Promise<string | null> {
    const cookie = CookieService.getCookie('https://pe.sjtu.edu.cn');
    hilog.info(0x0000, ApiService.TAG, 'cookies for pe.sjtu.edu.cn: %{public}s', cookie);

    const header: Record<string, string> = { 'User-Agent': 'okhttp/4.10.0' };
    if (cookie.length > 0) {
      header['Cookie'] = cookie;
    }

    const req = http.createHttp();
    try {
      const resp = await req.request('https://pe.sjtu.edu.cn/sports/my/uid', {
        method: http.RequestMethod.GET,
        header: header,
        expectDataType: http.HttpDataType.STRING,
        usingCache: false,
        connectTimeout: 15000,
        readTimeout: 15000
      });
      const body = resp.result as string;
      hilog.info(0x0000, ApiService.TAG, 'Raw response body: %{public}s', body);
      hilog.info(0x0000, ApiService.TAG, 'Response code: %{public}d', resp.responseCode);

      // 仅精准匹配 jAccount 登录页特征
      if (ApiService.isJAccountLoginPage(body) || resp.responseCode === 302 || resp.responseCode === 403) {
        hilog.info(0x0000, ApiService.TAG, 'Response is jAccount login page/redirect - cookie已过期');
        return null;
      }

      let parsed: Object | null = null;
      try {
        parsed = JSON.parse(body) as Object;
      } catch (e) {
        parsed = null;
      }

      if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
        const map = parsed as Record<string, Object>;
        if (ApiService.isCodeZero(map['code'])) {
          const data = map['data'] as Record<string, Object>;
          if (data !== undefined && data !== null && data['uid'] !== undefined) {
            return String(data['uid']);
          }
          return null;
        }
        hilog.info(0x0000, ApiService.TAG, 'API returned error code: %{public}s, message: %{public}s',
          JSON.stringify(map['code']), JSON.stringify(map['message']));
        return null;
      } else if (typeof parsed === 'string') {
        const uidString = parsed as string;
        hilog.info(0x0000, ApiService.TAG, 'API returned raw string: %{public}s', uidString);
        if (uidString.length > 0 && ApiService.looksLikeUid(uidString.trim())) {
          return uidString.trim();
        }
        return null;
      } else {
        hilog.info(0x0000, ApiService.TAG, 'Not valid JSON. Response might be HTML/plain text: %{public}s...',
          body.substring(0, Math.min(200, body.length)));
        const trimmedBody = body.trim();
        if (ApiService.looksLikeUid(trimmedBody)) {
          return trimmedBody;
        }
        return null;
      }
    } catch (e) {
      const err = e as BusinessError;
      hilog.error(0x0000, ApiService.TAG, 'getUid failed: %{public}d %{public}s', err.code, err.message);
      return null;
    } finally {
      req.destroy();
    }
  }

  /** 把 JSON 字段读取为 int（等价 Gson 的 JsonPrimitive.asInt），非法时返回 fallback */
  private static readInt(value: Object | undefined, fallback: number): number {
    if (typeof value === 'number') {
      // 不依赖 Math.trunc：数字统一走 parseInt(String(n))，截断语义一致且构造最保守
      const parsed = parseInt(String(value as number));
      return isNaN(parsed) ? fallback : parsed;
    }
    if (typeof value === 'string') {
      const parsed = parseInt(value as string);
      return isNaN(parsed) ? fallback : parsed;
    }
    return fallback;
  }

  /**
   * 异常 -> 可读文案。
   * catch 到的值不做 BusinessError 断言，统一按 Record 逐字段 typeof 校验，
   * 保证非 BusinessError（普通 Error / 任意抛出值）也能安全取到 message。
   */
  private static describeError(e: Object): string {
    if (typeof e !== 'object' || e === null) {
      return '未知错误';
    }
    const fields = e as Record<string, Object>;
    const messageVal = fields['message'];
    if (typeof messageVal === 'string') {
      const message = messageVal as string;
      if (message.length > 0) {
        return message;
      }
    }
    return '未知错误';
  }

  /**
   * 拉取跑步打卡规则（配速上下限、run id），失败时返回默认规则。
   * 迁移自 ApiService.getPointRules(): 先预热个人数据接口，再请求 point-rule。
   * 差异：OkHttp 的 connect/read 超时改用 http.request 的 connectTimeout/readTimeout，
   *       URLEncoder.encode(s, "UTF-8") 改用 encodeURIComponent（逗号同样编码为 %2C）。
   */
  async getPointRules(authToken: string, longitude: number, latitude: number): Promise<PointRules> {
    const defaultRules = ApiService.DEFAULT_POINT_RULES;
    const cookie = CookieService.getCookie(`https://${AppConfig.HOST}`);
    try {
      // 预热一次个人数据接口，失败不影响后续
      const warmUpHeader: Record<string, string> = {
        'User-Agent': ApiService.APP_USER_AGENT,
        'Accept': 'application/json, text/plain, */*',
        'Authorization': authToken
      };
      if (cookie.length > 0) {
        warmUpHeader['Cookie'] = cookie;
      }
      const warmUpReq = http.createHttp();
      try {
        await warmUpReq.request(AppConfig.MY_DATA_URL, {
          method: http.RequestMethod.GET,
          header: warmUpHeader,
          expectDataType: http.HttpDataType.STRING,
          usingCache: false,
          connectTimeout: 15000,
          readTimeout: 20000
        });
      } catch (e) {
        // 预热失败忽略，不写日志（与 Android runCatching 一致）
      } finally {
        warmUpReq.destroy();
      }

      const location = `${longitude.toFixed(14)},${latitude.toFixed(14)}`;
      const encodedLocation = encodeURIComponent(location);
      const ruleUrl = `${AppConfig.POINT_RULE_URL}?location=${encodedLocation}`;

      const header: Record<string, string> = {
        'User-Agent': ApiService.WEB_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Authorization': authToken,
        'Cache-Control': 'no-cache',
        'Referer': ruleUrl
      };
      if (cookie.length > 0) {
        header['Cookie'] = cookie;
      }

      const req = http.createHttp();
      try {
        const resp = await req.request(ruleUrl, {
          method: http.RequestMethod.GET,
          header: header,
          expectDataType: http.HttpDataType.STRING,
          usingCache: false,
          connectTimeout: 15000,
          readTimeout: 20000
        });
        const body = resp.result as string;
        if (resp.responseCode < 200 || resp.responseCode >= 300) {
          hilog.warn(0x0000, ApiService.TAG, 'getPointRules: HTTP %{public}d', resp.responseCode);
          return defaultRules;
        }
        // 与 getUid 一致的登录页判断：命中即视为 cookie 过期
        if (ApiService.isJAccountLoginPage(body)) {
          hilog.warn(0x0000, ApiService.TAG, 'getPointRules: 返回登录页，使用默认规则');
          return defaultRules;
        }

        let element: Object | null = null;
        try {
          element = JSON.parse(body) as Object;
        } catch (e) {
          element = null;
        }
        if (typeof element !== 'object' || element === null || Array.isArray(element)) {
          return defaultRules;
        }
        const root = element as Record<string, Object>;
        const dataVal = root['data'];
        if (typeof dataVal !== 'object' || dataVal === null || Array.isArray(dataVal)) {
          return defaultRules;
        }
        const data = dataVal as Record<string, Object>;
        const rulesVal = data['rules'];
        if (typeof rulesVal !== 'object' || rulesVal === null || Array.isArray(rulesVal)) {
          return defaultRules;
        }
        const rules = rulesVal as Record<string, Object>;

        const id = ApiService.readInt(rules['id'], 6);
        const spmin = ApiService.readInt(rules['spmin'], 180);
        const spmax = ApiService.readInt(rules['spmax'], 540);
        return new PointRules(id === 6 ? 9 : id, spmin, spmax);
      } finally {
        req.destroy();
      }
    } catch (e) {
      // 不做 BusinessError 断言，统一按 Object 读取 message
      const err = e as Object;
      hilog.warn(0x0000, ApiService.TAG, 'getPointRules 失败，使用默认规则: %{public}s',
        ApiService.describeError(err));
      return defaultRules;
    }
  }

  /**
   * 上传跑步数据
   * 迁移自 ApiService.upload(): POST JSON payload，Authorization 携带 uid（与 Android 一致）
   */
  async upload(authToken: string, payload: PayloadItem[]): Promise<UploadResult> {
    const cookie = CookieService.getCookie('https://pe.sjtu.edu.cn');
    const json = JSON.stringify(payload);

    const header: Record<string, string> = {
      'Authorization': authToken,
      'Content-Type': 'application/json; charset=utf-8'
    };
    if (cookie.length > 0) {
      header['Cookie'] = cookie;
    }

    const req = http.createHttp();
    try {
      const resp = await req.request('https://pe.sjtu.edu.cn/api/running/result/upload', {
        method: http.RequestMethod.POST,
        header: header,
        extraData: json,
        expectDataType: http.HttpDataType.STRING,
        usingCache: false,
        connectTimeout: 20000,
        readTimeout: 20000
      });
      const respBody = resp.result as string;
      hilog.info(0x0000, ApiService.TAG, 'Upload response code: %{public}d', resp.responseCode);
      hilog.info(0x0000, ApiService.TAG, 'Upload response body: %{public}s',
        respBody.substring(0, Math.min(200, respBody.length)));

      // 检测是否因 cookie 过期导致上传失败（复用 jAccount 登录页判断）
      if (ApiService.isJAccountLoginPage(respBody) || resp.responseCode === 403 || resp.responseCode === 401) {
        hilog.info(0x0000, ApiService.TAG, '上传失败，可能cookie已过期');
        return new UploadResult(false, 'cookie已过期，需要重新登录', true);
      }

      try {
        const resMap = JSON.parse(respBody) as Record<string, Object>;
        let code = -1;
        const rawCode = resMap['code'];
        if (typeof rawCode === 'number') {
          code = rawCode as number;
        } else if (typeof rawCode === 'string') {
          code = parseInt(rawCode as string);
          if (isNaN(code)) {
            code = -1;
          }
        }
        const message = resMap['message'] !== undefined ? String(resMap['message']) : '未知错误';
        return new UploadResult(code === 0, message, false);
      } catch (e) {
        return new UploadResult(false, respBody, false);
      }
    } catch (e) {
      const err = e as BusinessError;
      hilog.error(0x0000, ApiService.TAG, 'upload failed: %{public}d %{public}s', err.code, err.message);
      return new UploadResult(false, `网络请求失败: ${err.message}`, false);
    } finally {
      req.destroy();
    }
  }

  // ==================== 学期统计（只读） ====================

  /** JSON 值 -> 对象（非对象返回 undefined） */
  private static asObject(value: Object | undefined): Record<string, Object> | undefined {
    if (value === undefined || value === null || typeof value !== 'object' || Array.isArray(value)) {
      return undefined;
    }
    return value as Record<string, Object>;
  }

  /** obj[key] 指向对象时返回它（等价 Android 的 asObjectOrNull / objOf） */
  private static objOf(parent: Record<string, Object> | undefined, key: string): Record<string, Object> | undefined {
    if (parent === undefined) {
      return undefined;
    }
    return ApiService.asObject(parent[key]);
  }

  /** obj[key] 指向数组时返回其元素列表（等价 Android 的 arrOf） */
  private static arrOf(parent: Record<string, Object> | undefined, key: string): Object[] {
    if (parent === undefined) {
      return [];
    }
    const value = parent[key];
    if (value === undefined || value === null || !Array.isArray(value)) {
      return [];
    }
    return value as Object[];
  }

  /** 数组字段的第一个对象（等价 Android 的 firstObject）：服务器把 data 包成数组 */
  private static firstObject(parent: Object | undefined, key: string): Record<string, Object> | undefined {
    const root = ApiService.asObject(parent);
    const list = ApiService.arrOf(root, key);
    if (list.length === 0) {
      return undefined;
    }
    return ApiService.asObject(list[0]);
  }

  /** 字符串字段（等价 Android 的 stringOrNull，只接受真正的字符串） */
  private static stringOrNull(parent: Record<string, Object> | undefined, key: string): string | undefined {
    if (parent === undefined) {
      return undefined;
    }
    const value = parent[key];
    return typeof value === 'string' ? value as string : undefined;
  }

  /**
   * JSON 数值字段（等价 Android 的 jsonNumber）：
   * 数字或字符串都接受，去掉尾部 % 与千分位逗号，非法值返回 undefined。
   */
  private static jsonNumber(value: Object | undefined): number | undefined {
    let raw: string;
    if (typeof value === 'number') {
      raw = String(value as number);
    } else if (typeof value === 'string') {
      raw = value as string;
    } else {
      return undefined;
    }
    raw = raw.trim();
    while (raw.endsWith('%')) {
      raw = raw.substring(0, raw.length - 1);
    }
    raw = raw.replace(',', '');
    const parsed = Number(raw);
    if (raw.length === 0 || !Number.isFinite(parsed)) {
      return undefined;
    }
    return parsed;
  }

  /** 服务器日期形如 `2026-09-19 07:52:19`，只取前 10 个字符；解析不出返回 undefined */
  private static serverDate(text: string | undefined): Date | undefined {
    if (text === undefined || text.length < 10) {
      return undefined;
    }
    const parsed = parseDate(text.substring(0, 10));
    return parsed === null ? undefined : parsed;
  }

  /** `state == "0"` 计入成绩，12/13 等是无效记录 */
  private static countsTowardScore(value: Object | undefined): boolean {
    let text: string;
    if (typeof value === 'string') {
      text = (value as string).trim();
    } else if (typeof value === 'number') {
      return (value as number) === 0;
    } else {
      return false;
    }
    if (!/^[+-]?\d+$/.test(text)) {
      return false;
    }
    return parseInt(text) === 0;
  }

  /** 带会话 Cookie 的 GET，返回解析后的 JSON（失败抛错，由调用方决定是否忽略） */
  private async getJson(url: string, query: string, what: string): Promise<Object> {
    const cookie = CookieService.getCookie(`https://${AppConfig.HOST}`);
    const header: Record<string, string> = {
      'User-Agent': ApiService.APP_USER_AGENT,
      'Accept': 'application/json, text/plain, */*',
      'Referer': `https://${AppConfig.HOST}/phone/`
    };
    if (cookie.length > 0) {
      header['Cookie'] = cookie;
    }
    const req = http.createHttp();
    try {
      const resp = await req.request(query.length > 0 ? `${url}?${query}` : url, {
        method: http.RequestMethod.GET,
        header: header,
        expectDataType: http.HttpDataType.STRING,
        usingCache: false,
        connectTimeout: 15000,
        readTimeout: 20000
      });
      const body = resp.result as string;
      if (resp.responseCode < 200 || resp.responseCode >= 300) {
        throw new Error(`${what}请求失败: HTTP ${resp.responseCode}`);
      }
      if (ApiService.isJAccountLoginPage(body)) {
        throw new Error(`${what}请求返回登录页，cookie 已过期`);
      }
      return JSON.parse(body) as Object;
    } finally {
      req.destroy();
    }
  }

  /** 带会话 Cookie 的 POST（空 JSON 体），部分接口必须用 POST 才返回数据 */
  private async postEmptyJson(url: string, what: string): Promise<Object> {
    const cookie = CookieService.getCookie(`https://${AppConfig.HOST}`);
    const header: Record<string, string> = {
      'User-Agent': ApiService.APP_USER_AGENT,
      'Accept': 'application/json, text/plain, */*',
      'Referer': `https://${AppConfig.HOST}/phone/`,
      'Content-Type': 'application/json; charset=utf-8'
    };
    if (cookie.length > 0) {
      header['Cookie'] = cookie;
    }
    const req = http.createHttp();
    try {
      const resp = await req.request(url, {
        method: http.RequestMethod.POST,
        header: header,
        extraData: '{}',
        expectDataType: http.HttpDataType.STRING,
        usingCache: false,
        connectTimeout: 15000,
        readTimeout: 20000
      });
      const body = resp.result as string;
      if (resp.responseCode < 200 || resp.responseCode >= 300) {
        throw new Error(`${what}请求失败: HTTP ${resp.responseCode}`);
      }
      if (ApiService.isJAccountLoginPage(body)) {
        throw new Error(`${what}请求返回登录页，cookie 已过期`);
      }
      return JSON.parse(body) as Object;
    } finally {
      req.destroy();
    }
  }

  /**
   * 只读学期统计：达标公里、完成率、学期目标、学期起止与本学期打卡日期。
   * 迁移自 Android ApiService.semesterStats()。
   *
   * 这些接口只要 pe.sjtu.edu.cn 的会话 Cookie，不需要 /sports/my/uid 换的 token。
   * 其中学期目标与学期起止日期失败时不阻塞其余数据。
   *
   * 抛出的错误由调用方（MainViewModel.refreshSemesterStats）转成日志。
   */
  async semesterStats(): Promise<SemesterStats> {
    const stats = new SemesterStats();

    // 1) 本学期达标公里 / 总公里 / 完成率
    const summaryRoot = await this.getJson(AppConfig.MY_DATA_URL, '', '学期统计');
    const summary = ApiService.firstObject(summaryRoot, 'data');
    stats.resultKm = ApiService.jsonNumber(summary === undefined ? undefined : summary['resultKm']);
    stats.totalKm = ApiService.jsonNumber(summary === undefined ? undefined : summary['totalKm']);
    const percent = ApiService.jsonNumber(summary === undefined ? undefined : summary['percent']);
    // 服务器没给 percent 时用 达标/总公里 兜底
    stats.percent = percent !== undefined ? percent : percentFromRatio(stats.resultKm, stats.totalKm);

    // 2) 学期目标（失败不阻塞）
    try {
      const targetRoot = await this.getJson(AppConfig.SEMESTER_TARGET_URL, '', '学期目标');
      const targetData = ApiService.objOf(ApiService.asObject(targetRoot), 'data');
      stats.targetKm = ApiService.jsonNumber(targetData === undefined ? undefined : targetData['target']);
    } catch (e) {
      hilog.warn(0x0000, ApiService.TAG, '学期目标获取失败，忽略: %{public}s', ApiService.describeError(e as Object));
    }

    // 3) 当前学期 id 与名称
    const listRoot = await this.getJson(AppConfig.SEMESTER_LIST_URL, 'type=1', '学期列表');
    const entry = ApiService.firstObject(listRoot, 'data');
    const semesterId = entry === undefined ? undefined : ApiService.stringOrNull(entry, 'semesterId');
    if (semesterId === undefined || semesterId.trim().length === 0) {
      throw new Error('学期列表缺少 semesterId');
    }
    const rawName = entry === undefined ? undefined : ApiService.stringOrNull(entry, 'semesterName');
    if (rawName !== undefined && rawName.trim().length > 0) {
      stats.semesterName = rawName.trim();
    }

    // 4) 学期起止日期（失败不阻塞，日历退化为占位）
    try {
      const infoRoot = await this.postEmptyJson(AppConfig.USER_INFO_URL, '学期日期');
      const infoData = ApiService.objOf(ApiService.asObject(infoRoot), 'data');
      const dateEntry = ApiService.firstObject(infoData, 'semesterDateList');
      const start = ApiService.serverDate(dateEntry === undefined ? undefined : ApiService.stringOrNull(dateEntry,
        'startDate'));
      const end = ApiService.serverDate(dateEntry === undefined ? undefined : ApiService.stringOrNull(dateEntry,
        'endDate'));
      if (start !== undefined && end !== undefined) {
        stats.range = SemesterRange.of(start, end);
      }
    } catch (e) {
      hilog.warn(0x0000, ApiService.TAG, '学期日期获取失败，忽略: %{public}s', ApiService.describeError(e as Object));
    }

    // 5) 本学期全部跑步记录 -> 每天的打卡状态
    const recordsRoot = await this.getJson(AppConfig.RESULT_LIST_URL,
      `selectId=${encodeURIComponent(semesterId)}&type=1`, '跑步记录');
    const runDays = stats.runDays;
    const weeks = ApiService.arrOf(ApiService.asObject(recordsRoot), 'data');
    for (let w = 0; w < weeks.length; w++) {
      const week = ApiService.asObject(weeks[w]);
      const details = ApiService.arrOf(week, 'details');
      for (let d = 0; d < details.length; d++) {
        const record = ApiService.asObject(details[d]);
        if (record === undefined) {
          continue;
        }
        const date = ApiService.serverDate(ApiService.stringOrNull(record, 'timeFrom'));
        if (date === undefined) {
          continue;
        }
        const state = ApiService.countsTowardScore(record['state']) ? DayState.VALID : DayState.INVALID;
        recordDay(runDays, date, state);
      }
    }

    hilog.info(0x0000, ApiService.TAG, 'semesterStats ok: runDays=%{public}d range=%{public}s',
      runDays.size, stats.range === undefined ? '无' : '有');
    return stats;
  }
}

