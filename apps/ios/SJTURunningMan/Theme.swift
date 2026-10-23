//
//  Theme.swift
//  SJTURunningMan
//
//  品牌配色与尺寸，数值对齐安卓版 ui/theme/Color.kt 与 AppColors.kt。
//  颜色通过 UIColor 动态提供者适配亮/暗模式，无需在各视图里判断 colorScheme。
//

import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

enum AppTheme {
    /// 卡片统一圆角（对应 Android SectionShape = 20dp）。
    static let sectionCornerRadius: CGFloat = 20
    /// 控制台等小面板的圆角。
    static let panelCornerRadius: CGFloat = 14
    /// 控制台等宽字体（对应 ConsoleTextStyle 12sp Monospace）。
    static let consoleFont = Font.system(size: 12, weight: .regular, design: .monospaced)

    // MARK: - 品牌色

    static let primary = adaptive(light: 0x0B6BA5, dark: 0x8FCBF2)
    static let primaryLight = Color(rgb: 0x8FCBF2)
    static let primaryDark = Color(rgb: 0x004B71)
    static let tertiary = adaptive(light: 0x8D4E00, dark: 0xFFB684)

    // MARK: - 表面与文字

    static let background = adaptive(light: 0xF6F8FB, dark: 0x11151A)
    static let card = adaptive(light: 0xFFFFFF, dark: 0x1B2027)
    static let cardLow = adaptive(light: 0xEDF1F6, dark: 0x0B0F13)
    static let outlineVariant = adaptive(light: 0xDDE3EA, dark: 0x3E464C)
    static let outlineStrong = adaptive(light: 0xDDE3EA, dark: 0x40484E)
    static let onSurface = adaptive(light: 0x181C20, dark: 0xE1E7ED)
    static let onSurfaceVariant = adaptive(light: 0x40484E, dark: 0xBFC8CF)

    // MARK: - 状态色

    static let success = adaptive(light: 0x10B981, dark: 0x1F9E6B)
    static let warning = Color(rgb: 0xF59E0B)
    static let error = adaptive(light: 0xBA1A1A, dark: 0xFFB4AB)
    static let info = Color(rgb: 0x3B82F6)

    // MARK: - 控制台

    static let console = adaptive(light: 0x10151C, dark: 0x080C11)
    static let consoleOn = adaptive(light: 0xD7E3EE, dark: 0xC9D6E2)

    // MARK: - 学期日历

    static let runValid = adaptive(light: 0xA9DCB5, dark: 0x4F9C68)
    static let runInvalid = adaptive(light: 0xDCECD9, dark: 0x2F5C43)
    static let calendarEmpty = adaptive(light: 0xEEF2EF, dark: 0x26362E)
    static let calendarInk = adaptive(light: 0x1C3327, dark: 0xDCEBE0)

    // MARK: - 背景渐变

    static let gradientStart = adaptive(light: 0xD6ECFB, dark: 0x12293A)
}

/// 构造随系统亮暗自动切换的颜色。
private func adaptive(light: UInt32, dark: UInt32) -> Color {
    #if canImport(UIKit)
    return Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark ? UIColor(rgb: dark) : UIColor(rgb: light)
    })
    #else
    return Color(rgb: light)
    #endif
}

extension Color {
    /// 用 0xRRGGBB 形式的十六进制整数构造颜色。
    init(rgb: UInt32) {
        self.init(
            .sRGB,
            red: Double((rgb >> 16) & 0xFF) / 255.0,
            green: Double((rgb >> 8) & 0xFF) / 255.0,
            blue: Double(rgb & 0xFF) / 255.0,
            opacity: 1.0
        )
    }
}

#if canImport(UIKit)
extension UIColor {
    /// 用 0xRRGGBB 形式的十六进制整数构造颜色。
    convenience init(rgb: UInt32) {
        self.init(
            red: CGFloat((rgb >> 16) & 0xFF) / 255.0,
            green: CGFloat((rgb >> 8) & 0xFF) / 255.0,
            blue: CGFloat(rgb & 0xFF) / 255.0,
            alpha: 1.0
        )
    }
}
#endif
