//
//  AppConfig.swift
//  SJTURunningMan
//
//  与电脑版 / 安卓版保持一致的全局常量。
//

import Foundation

enum AppConfig {
    // MARK: - 版本与仓库

    static let versionName = "4.5.0"

    static let githubRepo = "JackyTJie/SJTURunningMan_Advanced_Edition"
    static let githubRepoURL = "https://github.com/\(githubRepo)"
    static let githubReleasesAPI = "https://api.github.com/repos/\(githubRepo)/releases"
    static let shuiyuanTopicURL = "https://shuiyuan.sjtu.edu.cn/t/topic/421786"

    // MARK: - 接口地址

    static let host = "pe.sjtu.edu.cn"
    static let uidURL = "https://pe.sjtu.edu.cn/sports/my/uid"
    static let myDataURL = "https://pe.sjtu.edu.cn/sports/my/data"
    static let pointRuleURL = "https://pe.sjtu.edu.cn/api/running/point-rule"
    static let uploadURL = "https://pe.sjtu.edu.cn/api/running/result/upload"
    static let semesterTargetURL = "https://pe.sjtu.edu.cn/sports/my/semesterTarget"
    static let semesterListURL = "https://pe.sjtu.edu.cn/sports/running/semester/list"
    static let userInfoURL = "https://pe.sjtu.edu.cn/sports/ranking/getUserInfo"
    static let resultListURL = "https://pe.sjtu.edu.cn/sports/running/result/list"

    // MARK: - 任务参数

    static let maxRunTimes = 30
    static let maxDistanceKm = 5.0
    static let minDistanceKm = 1.0
    static let defaultDistanceKm = 4.0
    static let defaultRunHour = 8
    static let defaultRunMinute = 0
    static let defaultRunSecond = 0
    static let intervalSeconds = 3

    static let startLatitude = 31.031599
    static let startLongitude = 121.442938

    // MARK: - 文案

    static let disclaimerText =
        "本项目仅用于学习、研究和技术测试，主要用于理解运动数据记录与上传相关的技术流程。\n\n" +
        "项目开发者反对任何违反学校规定的使用方式。\n\n" +
        "请在使用前确认自己的行为符合上海交通大学校规及相关法律法规的要求，" +
        "严禁用于伪造运动数据或规避体育锻炼要求。"

    static let commitmentText =
        "在继续使用本软件前，请认真阅读并作出承诺：\n\n" +
        "1. 我理解本项目仅用于学习、研究和技术测试，主要用于理解运动数据记录与上传相关的技术流程。\n\n" +
        "2. 我理解项目开发者反对任何违反学校规定的使用方式。\n\n" +
        "3. 我承诺在使用前确认自己的行为符合上海交通大学校规及相关法律法规的要求。\n\n" +
        "4. 我承诺不会将本软件用于伪造运动数据、规避体育锻炼要求或其他违规操作。"

    static let creditsText =
        "三改：Github@JackyTJie\n" +
        "二改：Github@accelerator-s\n" +
        "原作者：Github@Labyrinth0419"

    static let disclaimerShortText =
        "本项目仅供学习、研究和技术测试，请勿用于伪造运动数据或规避体育锻炼要求。"
}
