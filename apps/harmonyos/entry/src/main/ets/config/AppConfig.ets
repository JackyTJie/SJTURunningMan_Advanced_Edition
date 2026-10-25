/**
 * 应用配置常量
 * 迁移自 Android: com.sjtu.runner.config.AppConfig
 * 常量值逐字保持一致（版本号、上限、默认值、文案）。
 */
export class AppConfig {
  /** 版本号（与 AppScope/app.json5 的 versionName 保持一致） */
  static readonly VERSION_NAME: string = '4.5.0';
  static readonly GITHUB_REPO: string = 'JackyTJie/SJTURunningMan_Advanced_Edition';
  static readonly GITHUB_REPO_URL: string = 'https://github.com/JackyTJie/SJTURunningMan_Advanced_Edition';
  static readonly GITHUB_RELEASES_API: string =
    'https://api.github.com/repos/JackyTJie/SJTURunningMan_Advanced_Edition/releases';
  static readonly SHUIYUAN_TOPIC_URL: string = 'https://shuiyuan.sjtu.edu.cn/t/topic/421786';

  static readonly HOST: string = 'pe.sjtu.edu.cn';
  static readonly UID_URL: string = 'https://pe.sjtu.edu.cn/sports/my/uid';
  static readonly MY_DATA_URL: string = 'https://pe.sjtu.edu.cn/sports/my/data';
  static readonly POINT_RULE_URL: string = 'https://pe.sjtu.edu.cn/api/running/point-rule';
  static readonly UPLOAD_URL: string = 'https://pe.sjtu.edu.cn/api/running/result/upload';

  /** 跑步次数上限（与 Android/iOS 共享常量一致） */
  static readonly MAX_RUN_TIMES: number = 30;
  /** 目标距离上下限（km） */
  static readonly MAX_DISTANCE_KM: number = 5.0;
  static readonly MIN_DISTANCE_KM: number = 1.0;
  static readonly DEFAULT_DISTANCE_KM: number = 4.0;
  /** 默认开始时间 */
  static readonly DEFAULT_RUN_HOUR: number = 8;
  static readonly DEFAULT_RUN_MINUTE: number = 0;
  static readonly DEFAULT_RUN_SECOND: number = 0;
  /** 轨迹点采样间隔（秒） */
  static readonly INTERVAL_SECONDS: number = 3;
  /** 默认打卡点坐标（用于查询打卡规则，非路线首点） */
  static readonly START_LATITUDE: number = 31.031599;
  static readonly START_LONGITUDE: number = 121.442938;

  /** 运行日志保留条数上限 */
  static readonly MAX_LOG_ENTRIES: number = 400;
  /** 免责声明（关于页与底部提示共用） */
  static readonly DISCLAIMER_TEXT: string =
    '本项目仅用于学习、研究和技术测试，主要用于理解运动数据记录与上传相关的技术流程。\n\n' +
      '项目开发者反对任何违反学校规定的使用方式。\n\n' +
      '请在使用前确认自己的行为符合上海交通大学校规及相关法律法规的要求，严禁用于伪造运动数据或规避体育锻炼要求。';

  /** 使用承诺书（首次进入强制确认） */
  static readonly COMMITMENT_TEXT: string =
    '在继续使用本软件前，请认真阅读并作出承诺：\n\n' +
      '1. 我理解本项目仅用于学习、研究和技术测试，主要用于理解运动数据记录与上传相关的技术流程。\n\n' +
      '2. 我理解项目开发者反对任何违反学校规定的使用方式。\n\n' +
      '3. 我承诺在使用前确认自己的行为符合上海交通大学校规及相关法律法规的要求。\n\n' +
      '4. 我承诺不会将本软件用于伪造运动数据、规避体育锻炼要求或其他违规操作。';

  /** 作者署名（关于页） */
  static readonly CREDITS: string = '三改：Github@JackyTJie\n二改：Github@accelerator-s\n原作者：Github@Labyrinth0419';

  /**
   * 鸿蒙端维护者署名。
   * 与 CREDITS 分开：CREDITS 的四人名单四端一致，鸿蒙端维护者只在鸿蒙端展示。
   */
  static readonly HARMONYOS_CREDITS: string = '鸿蒙版维护：Github@AetherWish';
}
