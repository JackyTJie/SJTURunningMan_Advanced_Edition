//
//  Components.swift
//  SJTURunningMan
//
//  可复用 UI 组件，结构对齐安卓版 ui/components/。
//  卡片与按钮使用 Liquid Glass，适配 iOS 26/27 的新外观。
//

import SwiftUI

// MARK: - 卡片

/// 统一的分区卡片：可选标题行（图标 + 标题 + 副标题 + 尾部操作）与内容区。
struct SectionCard<Content: View, Action: View>: View {
    private let title: String?
    private let icon: String?
    private let supporting: String?
    private let elevated: Bool
    private let action: (() -> Action)?
    private let content: () -> Content

    init(
        title: String? = nil,
        icon: String? = "info.circle",
        supporting: String? = nil,
        elevated: Bool = false,
        @ViewBuilder action: @escaping () -> Action,
        @ViewBuilder content: @escaping () -> Content
    ) {
        self.title = title
        self.icon = icon
        self.supporting = supporting
        self.elevated = elevated
        self.action = action
        self.content = content
    }

    init(
        title: String? = nil,
        icon: String? = "info.circle",
        supporting: String? = nil,
        elevated: Bool = false,
        @ViewBuilder content: @escaping () -> Content
    ) where Action == EmptyView {
        self.init(
            title: title,
            icon: icon,
            supporting: supporting,
            elevated: elevated,
            action: { EmptyView() },
            content: content
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let title {
                HStack(spacing: 10) {
                    if let icon {
                        Image(systemName: icon)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(AppTheme.primary)
                            .frame(width: 20)
                    }
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(.headline)
                            .foregroundStyle(AppTheme.onSurface)
                        if let supporting {
                            Text(supporting)
                                .font(.caption)
                                .foregroundStyle(AppTheme.onSurfaceVariant)
                        }
                    }
                    Spacer(minLength: 0)
                    if let action {
                        action()
                    }
                }
            }
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 18)
        .padding(.top, title == nil ? 18 : 16)
        .padding(.bottom, 18)
        .glassEffect(.regular, in: RoundedRectangle(cornerRadius: AppTheme.sectionCornerRadius))
        .shadow(color: .black.opacity(elevated ? 0.16 : 0), radius: elevated ? 12 : 0, y: elevated ? 5 : 0)
    }
}

/// 卡片内部的分隔线。
struct SectionDivider: View {
    var body: some View {
        Rectangle()
            .fill(AppTheme.outlineVariant)
            .frame(maxWidth: .infinity)
            .frame(height: 1)
    }
}

// MARK: - 状态徽标

struct StatusPill: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.system(size: 12, weight: .semibold))
            .foregroundStyle(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color.opacity(0.16), in: RoundedRectangle(cornerRadius: 8))
            .frame(height: 24)
            .fixedSize()
    }
}

// MARK: - 状态卡片

struct StatItem: Identifiable {
    let id = UUID()
    let label: String
    let value: String

    init(_ label: String, _ value: String) {
        self.label = label
        self.value = value
    }
}

struct StatusCard: View {
    let progress: TaskProgress
    let headline: String
    let stats: [StatItem]

    var body: some View {
        SectionCard(elevated: true) {
            HStack(spacing: 12) {
                if progress.status.isActive {
                    ProgressView()
                        .controlSize(.regular)
                        .tint(AppTheme.primary)
                        .frame(width: 28, height: 28)
                }
                VStack(alignment: .leading, spacing: 2) {
                    Text(headline)
                        .font(.title2.weight(.semibold))
                        .foregroundStyle(AppTheme.onSurface)
                    Text(progress.status.label)
                        .font(.caption)
                        .foregroundStyle(AppTheme.onSurfaceVariant)
                }
                Spacer(minLength: 0)
                if progress.total > 0 {
                    Text("\(progress.current)/\(progress.total)")
                        .font(.headline)
                        .foregroundStyle(AppTheme.primary)
                }
            }

            if progress.total > 0 {
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Capsule().fill(AppTheme.cardLow)
                        Capsule()
                            .fill(AppTheme.primary)
                            .frame(width: max(0, geo.size.width * progress.fraction))
                    }
                }
                .frame(height: 8)
            }

            HStack(spacing: 10) {
                ForEach(stats) { item in
                    StatCell(label: item.label, value: item.value)
                }
            }
        }
    }
}

struct StatCell: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(AppTheme.onSurfaceVariant)
            Text(value)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(AppTheme.onSurface)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(AppTheme.cardLow, in: RoundedRectangle(cornerRadius: AppTheme.sectionCornerRadius))
    }
}

// MARK: - 控制台日志

struct ConsoleLog: View {
    let entries: [LogEntry]
    var placeholder: String = "就绪。点击「开始任务」启动。"

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                if entries.isEmpty {
                    Text(placeholder)
                        .font(AppTheme.consoleFont)
                        .foregroundStyle(AppTheme.consoleOn.opacity(0.55))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                } else {
                    VStack(alignment: .leading, spacing: 3) {
                        ForEach(entries) { entry in
                            HStack(alignment: .top, spacing: 8) {
                                Text(entry.time)
                                    .font(AppTheme.consoleFont)
                                    .foregroundStyle(AppTheme.consoleOn.opacity(0.45))
                                Text(entry.message)
                                    .font(AppTheme.consoleFont)
                                    .foregroundStyle(color(for: entry.level))
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .id(entry.id)
                        }
                    }
                    .padding(14)
                }
            }
            .onChange(of: entries.count) { _, _ in
                guard let last = entries.last else { return }
                withAnimation(.easeOut(duration: 0.2)) {
                    proxy.scrollTo(last.id, anchor: .bottom)
                }
            }
        }
        .background(AppTheme.console)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius)
                .stroke(AppTheme.outlineStrong.opacity(0.35), lineWidth: 1)
        )
    }

    private func color(for level: LogLevel) -> Color {
        switch level {
        case .info: return AppTheme.consoleOn
        case .success: return AppTheme.success
        case .warn: return AppTheme.warning
        case .error: return AppTheme.error
        }
    }
}

// MARK: - 流式布局（用于标签换行）

struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var totalHeight: CGFloat = 0
        var rowWidth: CGFloat = 0
        var rowHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            let needed = rowWidth == 0 ? size.width : rowWidth + spacing + size.width
            if needed > maxWidth, rowWidth > 0 {
                totalHeight += rowHeight + spacing
                rowWidth = size.width
                rowHeight = size.height
            } else {
                rowWidth = needed
                rowHeight = max(rowHeight, size.height)
            }
        }
        totalHeight += rowHeight
        return CGSize(width: maxWidth == .infinity ? rowWidth : maxWidth, height: totalHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) {
        var x = bounds.minX
        var y = bounds.minY
        var rowHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX, x > bounds.minX {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}

// MARK: - 选择控件

struct ChoiceChips: View {
    let options: [String]
    let selected: String
    let onSelect: (String) -> Void

    var body: some View {
        FlowLayout(spacing: 8) {
            ForEach(options, id: \.self) { option in
                let isSelected = option == selected
                Button {
                    onSelect(option)
                } label: {
                    Text(option)
                        .font(.subheadline.weight(isSelected ? .semibold : .regular))
                        .foregroundStyle(isSelected ? AppTheme.primary : AppTheme.onSurface)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(
                            isSelected ? AppTheme.primary.opacity(0.14) : Color.clear,
                            in: RoundedRectangle(cornerRadius: AppTheme.sectionCornerRadius)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: AppTheme.sectionCornerRadius)
                                .stroke(isSelected ? AppTheme.primary : AppTheme.outlineVariant, lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

struct NumberField: View {
    let value: String
    var label: String?
    var width: CGFloat = 64
    var maxLength: Int = 3
    let onChange: (String) -> Void

    @State private var text: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let label {
                Text(label)
                    .font(.caption2)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }
            TextField("", text: $text)
                .keyboardType(.numberPad)
                .multilineTextAlignment(.center)
                .font(.body.weight(.medium))
                .foregroundStyle(AppTheme.onSurface)
                .padding(.horizontal, 8)
                .padding(.vertical, 8)
                .frame(width: width)
                .background(AppTheme.cardLow, in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius)
                        .stroke(AppTheme.outlineVariant, lineWidth: 1)
                )
        }
        .onAppear { text = value }
        .onChange(of: text) { _, newValue in
            let filtered = String(newValue.filter(\.isNumber).prefix(maxLength))
            if filtered != newValue {
                text = filtered
            }
            onChange(filtered)
        }
        .onChange(of: value) { _, newValue in
            if newValue != text {
                text = newValue
            }
        }
    }
}

struct TimeField: View {
    let hour: Int
    let minute: Int
    let second: Int
    let onChange: (Int, Int, Int) -> Void

    @State private var selection: Date

    init(hour: Int, minute: Int, second: Int, onChange: @escaping (Int, Int, Int) -> Void) {
        self.hour = hour
        self.minute = minute
        self.second = second
        self.onChange = onChange
        _selection = State(initialValue: Self.makeDate(hour: hour, minute: minute, second: second))
    }

    var body: some View {
        DatePicker("开始时间", selection: $selection, displayedComponents: .hourAndMinute)
            .datePickerStyle(.wheel)
            .labelsHidden()
            .tint(AppTheme.primary)
            .frame(maxWidth: .infinity)
            .frame(height: 158)
            .clipped()
            .background(AppTheme.cardLow, in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
            .overlay {
                RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius)
                    .strokeBorder(AppTheme.outlineVariant, lineWidth: 1)
            }
            .accessibilityLabel("开始时间")
            .onChange(of: selection) { _, _ in publishSelection() }
            .onChange(of: hour) { _, _ in syncSelection() }
            .onChange(of: minute) { _, _ in syncSelection() }
            .onChange(of: second) { _, _ in syncSelection() }
    }

    private func publishSelection() {
        let parts = Calendar.current.dateComponents([.hour, .minute, .second], from: selection)
        let newHour = parts.hour ?? hour
        let newMinute = parts.minute ?? minute
        let newSecond = parts.second ?? second
        guard newHour != hour || newMinute != minute || newSecond != second else { return }
        onChange(newHour, newMinute, newSecond)
    }

    private func syncSelection() {
        let next = Self.makeDate(hour: hour, minute: minute, second: second)
        let current = Calendar.current.dateComponents([.hour, .minute, .second], from: selection)
        let nextParts = Calendar.current.dateComponents([.hour, .minute, .second], from: next)
        guard current.hour != nextParts.hour || current.minute != nextParts.minute || current.second != nextParts.second else {
            return
        }
        selection = next
    }

    private static func makeDate(hour: Int, minute: Int, second: Int) -> Date {
        let calendar = Calendar.current
        var parts = calendar.dateComponents([.year, .month, .day], from: Date())
        parts.hour = hour
        parts.minute = minute
        parts.second = second
        return calendar.date(from: parts) ?? Date()
    }
}

struct DistanceSlider: View {
    let distanceKm: Double
    let range: ClosedRange<Double>
    let onDistanceChange: (Double) -> Void

    var body: some View {
        VStack(spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(String(format: "%.1f", distanceKm))
                    .font(.title2.weight(.bold))
                    .foregroundStyle(AppTheme.primary)
                Text("km")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
                Spacer()
                Text("上限 \(Int(range.upperBound))km")
                    .font(.caption2)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }
            Slider(
                value: Binding(
                    get: { min(max(distanceKm, range.lowerBound), range.upperBound) },
                    set: { onDistanceChange(($0 * 10).rounded() / 10) }
                ),
                in: range,
                step: 0.1
            )
            .tint(AppTheme.primary)
        }
    }
}

struct RouteOption: Identifiable {
    let id: String
    let title: String
    let subtitle: String?
    let selected: Bool

    init(id: String, title: String, subtitle: String? = nil, selected: Bool = false) {
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.selected = selected
    }
}

struct MenuDropdown: View {
    let value: String
    var label: String?
    let options: [RouteOption]
    let onSelect: (RouteOption) -> Void

    var body: some View {
        Menu {
            ForEach(options) { option in
                Button {
                    onSelect(option)
                } label: {
                    if let subtitle = option.subtitle {
                        Text("\(option.title)（\(subtitle)）")
                    } else {
                        Text(option.title)
                    }
                }
            }
        } label: {
            HStack(spacing: 8) {
                VStack(alignment: .leading, spacing: 2) {
                    if let label {
                        Text(label)
                            .font(.caption2)
                            .foregroundStyle(AppTheme.onSurfaceVariant)
                    }
                    Text(value)
                        .font(.body.weight(.medium))
                        .foregroundStyle(AppTheme.onSurface)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
                Image(systemName: "chevron.up.chevron.down")
                    .font(.caption)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity)
            .background(AppTheme.cardLow, in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius)
                    .stroke(AppTheme.outlineVariant, lineWidth: 1)
            )
        }
    }
}

// MARK: - 路线预览画布

/// 按路线坐标绘制等比轮廓，跳段用红色高亮，对齐安卓版 RoutePreviewCanvas。
struct RoutePreviewCanvas: View {
    let samples: [TrackSample]
    var jumpCount: Int = 0

    var body: some View {
        ZStack {
            if samples.count < 2 {
                Text("暂无可预览路线")
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            } else {
                Canvas { context, size in
                    draw(in: &context, size: size)
                }
            }
        }
    }

    private func draw(in context: inout GraphicsContext, size: CGSize) {
        let lons = samples.map(\.longitude)
        let lats = samples.map(\.latitude)
        guard let minLon = lons.min(), let maxLon = lons.max(),
              let minLat = lats.min(), let maxLat = lats.max() else { return }

        let spanLon = max(maxLon - minLon, 1e-6)
        let spanLat = max(maxLat - minLat, 1e-6)
        // 纬度方向按 cos(lat) 压缩，保证形状比例正确
        let latScale = cos((minLat + maxLat) / 2 * .pi / 180)

        let inset: Double = 12
        let availableW = Double(size.width) - inset * 2
        let availableH = Double(size.height) - inset * 2
        let scale = min(availableW / spanLon, availableH / (spanLat * latScale))

        let drawnW = spanLon * scale
        let drawnH = spanLat * latScale * scale
        let offsetX = (Double(size.width) - drawnW) / 2
        let offsetY = (Double(size.height) - drawnH) / 2

        func point(_ sample: TrackSample) -> CGPoint {
            CGPoint(
                x: offsetX + (sample.longitude - minLon) * scale,
                y: offsetY + (maxLat - sample.latitude) * scale * latScale
            )
        }

        var path = Path()
        path.move(to: point(samples[0]))
        for sample in samples.dropFirst() {
            path.addLine(to: point(sample))
        }
        context.stroke(
            path,
            with: .color(AppTheme.primary.opacity(0.85)),
            style: StrokeStyle(lineWidth: 2.5, lineCap: .round, dash: [6, 3])
        )

        if jumpCount > 0 {
            for i in 0..<(samples.count - 1) {
                let a = samples[i]
                let b = samples[i + 1]
                let distance = GpsUtil.haversineDistance(
                    lat1: a.latitude, lon1: a.longitude,
                    lat2: b.latitude, lon2: b.longitude
                )
                if distance > DataGenerator.jumpThresholdM {
                    var segment = Path()
                    segment.move(to: point(a))
                    segment.addLine(to: point(b))
                    context.stroke(
                        segment,
                        with: .color(AppTheme.error.opacity(0.9)),
                        style: StrokeStyle(lineWidth: 3, lineCap: .round)
                    )
                }
            }
        }

        let start = point(samples[0])
        let end = point(samples[samples.count - 1])
        let ring = { (center: CGPoint) in
            Path(ellipseIn: CGRect(x: center.x - 9, y: center.y - 9, width: 18, height: 18))
        }
        let dot = { (center: CGPoint) in
            Path(ellipseIn: CGRect(x: center.x - 6, y: center.y - 6, width: 12, height: 12))
        }
        context.stroke(ring(start), with: .color(AppTheme.outlineVariant.opacity(0.6)), lineWidth: 1)
        context.stroke(ring(end), with: .color(AppTheme.outlineVariant.opacity(0.6)), lineWidth: 1)
        context.fill(dot(start), with: .color(AppTheme.success))
        context.fill(dot(end), with: .color(AppTheme.tertiary))
    }
}

// MARK: - 底部免责声明

struct DisclaimerNotice: View {
    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 16))
                .foregroundStyle(AppTheme.warning)
            Text(AppConfig.disclaimerShortText)
                .font(.footnote)
                .foregroundStyle(AppTheme.onSurface)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(AppTheme.warning.opacity(0.12), in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
    }
}

// MARK: - 本学期进度

/// 「本学期进度」卡片：只读展示当前学期的达标公里与完成率，未登录时两个数值都是 `--`。
struct SemesterCard: View {
    let loggedIn: Bool
    let kmText: String
    let percentText: String

    var body: some View {
        SectionCard(
            title: "本学期进度",
            icon: "chart.bar.xaxis",
            supporting: loggedIn
                ? "登录状态下自动同步，只读展示当前学期。"
                : "登录账号后自动同步本学期数据。"
        ) {
            SectionDivider()
            HStack(spacing: 14) {
                SemesterMetric(label: "达标公里", value: kmText)
                SemesterMetric(label: "完成率", value: percentText)
            }
        }
    }
}

private struct SemesterMetric: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption)
                .foregroundStyle(AppTheme.onSurfaceVariant)
            Text(value)
                .font(.title2.weight(.bold))
                .foregroundStyle(AppTheme.primary)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// MARK: - 学期日历

private let weekLabels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

/// 周一起始，逐月展开本学期每一天。
///
/// 实心绿 = 计入成绩，描边 = 有记录但未计入，灰 = 未跑，空白格 = 补齐或不在学期内。
struct SemesterCalendar: View {
    let loggedIn: Bool
    let weeks: [CalendarWeek]

    var body: some View {
        SectionCard(
            title: "学期日历",
            icon: "calendar",
            supporting: loggedIn
                ? "实心绿=计入成绩，描边=无效记录，灰=未跑。"
                : "登录后显示本学期打卡记录。"
        ) {
            SectionDivider()
            HStack(spacing: 0) {
                ForEach(weekLabels, id: \.self) { label in
                    Text(label)
                        .font(.caption2)
                        .foregroundStyle(AppTheme.onSurfaceVariant)
                        .frame(maxWidth: .infinity)
                }
            }
            VStack(spacing: 2) {
                ForEach(Array(weeks.enumerated()), id: \.offset) { _, week in
                    VStack(spacing: 2) {
                        Text(week.title)
                            .font(.caption2)
                            .foregroundStyle(AppTheme.onSurfaceVariant)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .frame(height: week.title.isEmpty ? 0 : 18)
                        HStack(spacing: 0) {
                            ForEach(Array(week.days.enumerated()), id: \.offset) { _, day in
                                CalendarDayCell(day: day)
                                    .frame(maxWidth: .infinity)
                            }
                        }
                    }
                }
            }
            if weeks.isEmpty {
                Text("服务器未返回本学期起止日期。")
                    .font(.caption)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }
        }
    }
}

private struct CalendarDayCell: View {
    let day: CalendarDay

    var body: some View {
        ZStack {
            if day.day > 0 {
                // 无效记录只描边，不填实心绿，和电脑版 DayCell 一致。
                Circle()
                    .fill(background)
                    .overlay(
                        day.state == .invalid
                            ? Circle().strokeBorder(AppTheme.primary, lineWidth: 1)
                            : nil
                    )
                    .frame(width: 24, height: 24)
                Text("\(day.day)")
                    .font(.system(size: 11, weight: day.state == .valid ? .semibold : .regular))
                    .foregroundStyle(AppTheme.calendarInk)
            }
        }
        .frame(height: 26)
    }

    private var background: Color {
        switch day.state {
        case .valid: return AppTheme.runValid
        case .invalid: return AppTheme.runInvalid
        case .none: return AppTheme.calendarEmpty
        }
    }
}

// MARK: - 跳过已有记录的日期

/// 开关行，沿用品牌蓝和统一的卡片底色。
struct SkipExistingRow: View {
    let checked: Bool
    let enabled: Bool
    let onCheckedChange: (Bool) -> Void

    var body: some View {
        HStack(spacing: 10) {
            Toggle("", isOn: Binding(get: { checked }, set: onCheckedChange))
                .labelsHidden()
                .toggleStyle(.switch)
                .tint(AppTheme.primary)
                .disabled(!enabled)
            VStack(alignment: .leading, spacing: 2) {
                Text("跳过已有记录的日期")
                    .font(.subheadline)
                    .foregroundStyle(AppTheme.onSurface)
                Text("已有记录的那几天挪到更早日期。")
                    .font(.caption)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(AppTheme.cardLow, in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
        .overlay {
            RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius)
                .strokeBorder(AppTheme.outlineVariant, lineWidth: 1)
        }
    }
}

// MARK: - 浮层提示

/// 贴在顶栏下方浮在内容之上，不再把下方内容往下推。
struct NoticeOverlay: View {
    let notice: Notice?

    var body: some View {
        if let notice {
            Text(notice.text)
                .font(.callout)
                .foregroundStyle(AppTheme.onSurface)
                .multilineTextAlignment(.leading)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .glassEffect(.regular, in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
                .transition(.opacity)
                .id(notice.id)
        }
    }
}

// MARK: - 关于软件

/// 与电脑版的三张卡片一一对应 —— 软件信息、更新与社区、使用说明。
///
/// 更新检查只在点击「检查更新」时发起，结果只以一行文字呈现，不弹窗。
struct AboutPanel: View {
    @State private var result: UpdateResult?
    @State private var checking = false

    var body: some View {
        VStack(spacing: 14) {
            SectionCard(title: "交我润", icon: "info.circle") {
                HStack(spacing: 10) {
                    Text("SJTU RunningMan")
                        .font(.title3.weight(.semibold))
                        .foregroundStyle(AppTheme.onSurface)
                    StatusPill(text: "v\(AppConfig.versionName)", color: AppTheme.primary)
                    Spacer(minLength: 0)
                }
                Text("iOS 客户端 · Swift 与 SwiftUI")
                    .font(.caption)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
                SectionDivider()
                Text(AppConfig.creditsText)
                    .font(.caption)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }

            SectionCard(title: "更新与社区", icon: "arrow.down.circle") {
                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(statusColor)
                HStack(spacing: 10) {
                    if checking {
                        HStack(spacing: 8) {
                            ProgressView().controlSize(.small)
                            Text("检查中…").font(.subheadline)
                        }
                    } else {
                        Button {
                            checking = true
                        } label: {
                            Label("检查更新", systemImage: "arrow.clockwise")
                        }
                        .buttonStyle(.glass)
                    }
                    Spacer(minLength: 0)
                }
                SectionDivider()
                HStack(spacing: 8) {
                    linkButton("仓库", "chevron.left.forwardslash.chevron.right", AppConfig.githubRepoURL)
                    linkButton("水源", "arrow.up.right.square", AppConfig.shuiyuanTopicURL)
                    if case .updateAvailable(_, let latest) = result {
                        linkButton("下载", "arrow.down.circle", latest.url)
                    }
                }
            }

            SectionCard(title: "使用说明", icon: "text.document") {
                Text(AppConfig.disclaimerText)
                    .font(.caption)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .task(id: checking) {
            guard checking else { return }
            result = await UpdateChecker.checkForUpdates()
            checking = false
        }
    }

    private var statusText: String {
        switch result {
        case .upToDate(_, let latestTag): return "已是最新版本 \(latestTag)"
        case .updateAvailable(_, let latest): return "发现新版本 \(latest.tag)"
        case .failed(let reason): return "检查更新失败：\(reason)"
        case .none: return "尚未检查更新。"
        }
    }

    private var statusColor: Color {
        switch result {
        case .upToDate, .updateAvailable: return AppTheme.success
        case .failed: return AppTheme.error
        case .none: return AppTheme.onSurfaceVariant
        }
    }

    @ViewBuilder
    private func linkButton(_ title: String, _ systemImage: String, _ urlString: String) -> some View {
        if let url = URL(string: urlString), !urlString.isEmpty {
            Link(destination: url) {
                Label(title, systemImage: systemImage)
                    .font(.footnote.weight(.medium))
            }
            .buttonStyle(.glass)
        }
    }
}

// MARK: - 悬浮玻璃标签栏

struct LiquidTabItem: Identifiable {
    let id: Int
    let title: String
    let systemImage: String
}

/// 悬浮式 Liquid Glass 标签栏。
/// 支持点击、左右滑动切页，以及按住选中胶囊横向拖动后吸附到最近一项。
struct LiquidTabBar: View {
    @Binding var selection: Int
    let items: [LiquidTabItem]

    @State private var dragPosition: CGFloat?
    @State private var dragIndex: Int?

    private var selectedIndex: Int {
        items.firstIndex(where: { $0.id == selection }) ?? 0
    }

    private var activeIndex: Int {
        dragIndex ?? selectedIndex
    }

    var body: some View {
        GeometryReader { proxy in
            let inset: CGFloat = 7
            let itemWidth = max((proxy.size.width - inset * 2) / CGFloat(max(items.count, 1)), 1)
            let indicatorWidth = max(itemWidth - 8, 1)
            let position = dragPosition ?? CGFloat(selectedIndex)

            ZStack(alignment: .leading) {
                selectionIndicator
                    .frame(width: indicatorWidth, height: 50)
                    .offset(x: inset + itemWidth * position + 4)
                    .animation(
                        dragPosition == nil ? .snappy(duration: 0.34, extraBounce: 0.10) : nil,
                        value: position
                    )

                HStack(spacing: 0) {
                    ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                        let isActive = index == activeIndex
                        Button {
                            select(item)
                        } label: {
                            VStack(spacing: 2) {
                                Image(systemName: item.systemImage)
                                    .font(.system(size: 17, weight: isActive ? .semibold : .regular))
                                    .symbolRenderingMode(.monochrome)
                                    .frame(width: 22, height: 18)
                                Text(item.title)
                                    .font(.system(size: 10, weight: isActive ? .semibold : .medium))
                                    .lineLimit(1)
                                    .minimumScaleFactor(0.72)
                            }
                            .foregroundStyle(isActive ? AppTheme.primary : AppTheme.onSurfaceVariant.opacity(0.82))
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .frame(width: itemWidth, height: 50)
                        .accessibilityLabel(item.title)
                        .accessibilityValue(item.id == selection ? "已选中" : "")
                    }
                }
                .padding(.horizontal, inset)
                .animation(.easeOut(duration: 0.16), value: activeIndex)
            }
            .frame(width: proxy.size.width, height: 64)
            .glassEffect(.regular, in: Capsule())
            .overlay {
                Capsule()
                    .strokeBorder(
                        LinearGradient(
                            colors: [.white.opacity(0.52), .white.opacity(0.05)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 0.8
                    )
            }
            .shadow(color: .black.opacity(0.18), radius: 20, y: 8)
            .contentShape(Capsule())
            .simultaneousGesture(dragGesture(itemWidth: itemWidth, inset: inset))
            .sensoryFeedback(.selection, trigger: activeIndex)
        }
        .frame(height: 64)
    }

    private var selectionIndicator: some View {
        Capsule()
            .fill(
                LinearGradient(
                    colors: [
                        AppTheme.primary.opacity(0.38),
                        AppTheme.primary.opacity(0.16)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .overlay {
                Capsule()
                    .strokeBorder(
                        LinearGradient(
                            colors: [.white.opacity(0.68), .white.opacity(0.08)],
                            startPoint: .top,
                            endPoint: .bottom
                        ),
                        lineWidth: 0.9
                    )
            }
            .overlay(alignment: .top) {
                Capsule()
                    .fill(.white.opacity(0.30))
                    .frame(height: 1)
                    .padding(.horizontal, 18)
            }
            .shadow(color: AppTheme.primary.opacity(0.26), radius: 10, y: 4)
            .allowsHitTesting(false)
    }

    private func select(_ item: LiquidTabItem) {
        guard item.id != selection else { return }
        withAnimation(.snappy(duration: 0.32, extraBounce: 0.10)) {
            selection = item.id
        }
    }

    private func dragGesture(itemWidth: CGFloat, inset: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .local)
            .onChanged { value in
                guard !items.isEmpty else { return }
                let rawPosition = (value.location.x - inset) / itemWidth - 0.5
                let position = min(max(rawPosition, 0), CGFloat(items.count - 1))
                dragPosition = position
                dragIndex = Int(position.rounded())
            }
            .onEnded { _ in
                guard !items.isEmpty else { return }
                let targetIndex = dragIndex ?? selectedIndex
                withAnimation(.snappy(duration: 0.34, extraBounce: 0.12)) {
                    if items.indices.contains(targetIndex) {
                        selection = items[targetIndex].id
                    }
                    dragPosition = nil
                    dragIndex = nil
                }
            }
    }
}
