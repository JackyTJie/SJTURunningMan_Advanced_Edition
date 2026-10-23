//
//  MainView.swift
//  SJTURunningMan
//
//  主界面：四个页面 —— 工作台 / 路线 / 任务日志 / 关于软件。
//  卡片与按钮采用 iOS 26/27 Liquid Glass 外观。
//

import SwiftUI

private let navTabs: [LiquidTabItem] = [
    LiquidTabItem(id: 0, title: "工作台", systemImage: "figure.run"),
    LiquidTabItem(id: 1, title: "路线", systemImage: "map"),
    LiquidTabItem(id: 2, title: "任务日志", systemImage: "terminal"),
    LiquidTabItem(id: 3, title: "关于软件", systemImage: "info.circle")
]

struct MainView: View {
    @State private var viewModel = MainViewModel()

    @Environment(\.verticalSizeClass) private var verticalSizeClass

    // 弹窗与导航
    @State private var tab = 0
    @State private var showLogin = false
    @State private var showRouteDesign = false
    @State private var showDatePicker = false
    @State private var showCommitment = false
    @State private var routeToDelete: RouteInfo?

    // 任务参数
    @State private var days = 1
    @State private var showCustomDays = false
    @State private var customDaysText = ""
    @State private var hour = AppConfig.defaultRunHour
    @State private var minute = AppConfig.defaultRunMinute
    @State private var second = AppConfig.defaultRunSecond
    @State private var distanceKm = AppConfig.defaultDistanceKm
    @State private var startDate = Calendar.current.date(byAdding: .day, value: -1, to: Date()) ?? Date()

    @AppStorage("commitment_accepted") private var commitmentAccepted = false

    private static let dateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private var isCompact: Bool { verticalSizeClass == .compact }
    private var logHeight: CGFloat { isCompact ? 150 : 210 }
    private var previewHeight: CGFloat { isCompact ? 120 : 150 }

    private var dateText: String { Self.dateFormatter.string(from: startDate) }
    private var daysLabel: String { showCustomDays ? "自定义" : "\(days)" }

    private var config: RunConfig {
        RunConfig(days: days, distanceKm: distanceKm, hour: hour, minute: minute, second: second, startDate: startDate)
    }

    var body: some View {
        ZStack {
            NavigationStack {
                ZStack {
                    backgroundGradient

                    TabView(selection: $tab) {
                        tabPage(for: 0) { workbenchTab }
                        tabPage(for: 1) { routesTab }
                        tabPage(for: 2) { logsTab }
                        tabPage(for: 3) { AboutPanel() }
                    }
                    .tabViewStyle(.page(indexDisplayMode: .never))
                }
                .navigationTitle("交我润")
                .navigationBarTitleDisplayMode(.inline)
                .toolbarBackgroundVisibility(.hidden, for: .navigationBar)
                .toolbar { toolbarContent }
                .safeAreaInset(edge: .bottom) { bottomArea }
            }

            noticeLayer
            dialogLayer
        }
        .animation(.easeInOut(duration: 0.2), value: showCommitment)
        .animation(.easeInOut(duration: 0.2), value: viewModel.notice?.id)
        .animation(.easeInOut(duration: 0.2), value: viewModel.routeConflict)
        .animation(.easeInOut(duration: 0.2), value: routeToDelete)
        .animation(.snappy(duration: 0.32, extraBounce: 0.06), value: tab)
        .task(id: config) { viewModel.updateConfig(config) }
        // 自动排计划生效后把界面上的次数与距离一起对齐。
        .onChange(of: viewModel.autoPlanApplied) { _, applied in
            guard let applied else { return }
            days = applied.runs
            distanceKm = applied.distanceKm
            showCustomDays = false
        }
        .onAppear {
            if !commitmentAccepted {
                showCommitment = true
            }
        }
        .sheet(isPresented: $showLogin) {
            LoginView {
                showLogin = false
                viewModel.onLoginSucceeded()
            }
        }
        .sheet(isPresented: $showRouteDesign, onDismiss: { viewModel.refreshRoutes() }) {
            RouteDesignView()
        }
        .sheet(isPresented: $showDatePicker) {
            DatePickerSheet(date: $startDate)
        }
    }

    // MARK: - 背景与工具栏

    private var backgroundGradient: some View {
        ZStack {
            AppTheme.background

            LinearGradient(
                colors: [AppTheme.gradientStart.opacity(0.72), AppTheme.background.opacity(0.2)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(AppTheme.primary.opacity(0.14))
                .frame(width: 320, height: 320)
                .blur(radius: 80)
                .offset(x: -150, y: -290)

            Circle()
                .fill(AppTheme.tertiary.opacity(0.10))
                .frame(width: 280, height: 280)
                .blur(radius: 90)
                .offset(x: 170, y: -70)
        }
        .ignoresSafeArea()
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            Button {
                showLogin = true
            } label: {
                Image(systemName: viewModel.loggedIn ? "person.crop.circle.badge.checkmark" : "person.crop.circle.badge.exclamationmark")
                    .symbolRenderingMode(.hierarchical)
                    .foregroundStyle(viewModel.loggedIn ? AppTheme.primary : AppTheme.warning)
            }
            .accessibilityLabel(viewModel.loggedIn ? "账号已登录，点按重新登录" : "未登录，点按登录")
        }
    }

    /// 每个标签页保留独立的滚动位置，同时允许左右滑动切页。
    private func tabPage<Content: View>(for index: Int, @ViewBuilder content: () -> Content) -> some View {
        ScrollView {
            VStack(spacing: 14) {
                content()
                Spacer().frame(height: 8)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
        .scrollIndicators(.hidden)
        .tag(index)
    }

    // MARK: - 工作台

    @ViewBuilder
    private var workbenchTab: some View {
        StatusCard(
            progress: viewModel.progress,
            headline: "\(days) 次 · \(String(format: "%.1f", distanceKm)) km",
            stats: [
                StatItem("次数", "\(days)"),
                StatItem("距离", String(format: "%.1f km", distanceKm)),
                StatItem("时间", String(format: "%02d:%02d:%02d", hour, minute, second))
            ]
        )
        SemesterCard(
            loggedIn: viewModel.loggedIn,
            kmText: viewModel.semester.kmText,
            percentText: viewModel.semester.percentText
        )
        if viewModel.reloginRequired {
            reloginBanner
        }
        settingsSection
        DisclaimerNotice()
    }

    private var reloginBanner: some View {
        SectionCard(title: "Cookie 已过期", icon: "exclamationmark.triangle", elevated: true) {
            HStack(spacing: 10) {
                Text("登录状态失效，请重新登录后继续上传。")
                    .font(.callout)
                    .foregroundStyle(AppTheme.onSurface)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Button {
                    showLogin = true
                } label: {
                    Text("登录")
                }
                .buttonStyle(.glassProminent)
            }
        }
    }

    // MARK: - 路线

    private var routesTab: some View {
        SectionCard(
            title: "跑步路线",
            icon: "point.topleft.down.curvedto.point.bottomright.up",
            supporting: viewModel.selectedRoute.map { "\($0.pointCount) 个坐标点" } ?? "请选择路线",
            action: {
                Button {
                    showRouteDesign = true
                } label: {
                    Image(systemName: "plus")
                }
                .accessibilityLabel("设计新路线")
            }
        ) {
            VStack(alignment: .leading, spacing: 12) {
                MenuDropdown(
                    value: viewModel.selectedRoute?.name ?? "请选择路线",
                    label: "预设路线",
                    options: viewModel.routes.map { route in
                        RouteOption(
                            id: route.id,
                            title: route.name,
                            subtitle: "\(route.pointCount) 个点" + (route.isDefault ? " · 内置" : ""),
                            selected: viewModel.selectedRoute?.id == route.id
                        )
                    },
                    onSelect: { option in
                        if let route = viewModel.routes.first(where: { $0.id == option.id }) {
                            viewModel.selectRoute(route)
                        }
                    }
                )

                RoutePreviewCanvas(
                    samples: viewModel.preview?.samples ?? [],
                    jumpCount: viewModel.preview?.jumpCount ?? 0
                )
                .frame(maxWidth: .infinity)
                .frame(height: previewHeight)
                .background(AppTheme.cardLow)
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))

                HStack(alignment: .center, spacing: 10) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(viewModel.preview?.title ?? "路线预览")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.onSurface)
                        Text(viewModel.preview?.summary ?? "点击「预览路线」按当前设置离线生成")
                            .font(.caption)
                            .foregroundStyle(AppTheme.onSurfaceVariant)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    let jumps = viewModel.preview?.jumpCount ?? 0
                    if jumps > 0 {
                        StatusPill(text: "\(jumps) 处跳段", color: AppTheme.error)
                    }
                }

                SectionDivider()

                HStack(spacing: 8) {
                    Button {
                        viewModel.previewRoute()
                    } label: {
                        Label("预览路线", systemImage: "map")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.glass)
                    .disabled(viewModel.running || viewModel.selectedRoute == nil)

                    Button {
                        routeToDelete = viewModel.selectedRoute
                    } label: {
                        Label("删除路线", systemImage: "trash")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.glass)
                    .tint(AppTheme.error)
                    .disabled(viewModel.running || viewModel.selectedRoute == nil || viewModel.selectedRoute?.isDefault == true)
                }

                Button {
                    showRouteDesign = true
                } label: {
                    Label("设计新路线", systemImage: "plus")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.glassProminent)
                .disabled(viewModel.running)
            }
        }
    }

    // MARK: - 任务设置

    private var settingsSection: some View {
        SectionCard(title: "任务设置", icon: "calendar") {
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("跑步次数")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.onSurface)

                    if showCustomDays {
                        HStack(spacing: 8) {
                            NumberField(value: customDaysText, label: "次数 1-30", width: 140, maxLength: 2) { value in
                                customDaysText = value
                            }
                            Button {
                                if let value = Int(customDaysText) {
                                    days = min(max(value, 1), AppConfig.maxRunTimes)
                                }
                                showCustomDays = false
                            } label: {
                                Text("确定")
                            }
                            .buttonStyle(.glass)
                        }
                    } else {
                        ChoiceChips(
                            options: ["1", "3", "5", "7", "10", "15", "30", "自定义"],
                            selected: daysLabel,
                            onSelect: { option in
                                if option == "自定义" {
                                    showCustomDays = true
                                    customDaysText = "\(days)"
                                } else if let value = Int(option) {
                                    days = value
                                }
                            }
                        )
                    }
                }

                SectionDivider()

                VStack(alignment: .leading, spacing: 6) {
                    Text("开始时间")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.onSurface)
                    TimeField(hour: hour, minute: minute, second: second) { h, m, s in
                        hour = h
                        minute = m
                        second = s
                    }
                    Text("每次跑步自动加入 ±10 分钟 / ±30 秒随机波动")
                        .font(.caption)
                        .foregroundStyle(AppTheme.onSurfaceVariant)
                }

                SectionDivider()

                VStack(alignment: .leading, spacing: 6) {
                    Text("结束日期")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(AppTheme.onSurface)

                    Button {
                        if !viewModel.running {
                            showDatePicker = true
                        }
                    } label: {
                        HStack {
                            Text(dateText)
                                .font(.body)
                                .foregroundStyle(AppTheme.onSurface)
                            Spacer(minLength: 0)
                            Image(systemName: "calendar")
                                .foregroundStyle(AppTheme.primary)
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
                        .frame(maxWidth: .infinity)
                        .background(AppTheme.cardLow, in: RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
                        .overlay(
                            RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius)
                                .stroke(AppTheme.outlineVariant, lineWidth: 1)
                        )
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .disabled(viewModel.running)
                }

                SkipExistingRow(
                    checked: viewModel.skipExisting,
                    enabled: !viewModel.running,
                    onCheckedChange: { viewModel.setSkipExisting($0) }
                )

                SectionDivider()

                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 8) {
                        Image(systemName: "ruler")
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundStyle(AppTheme.primary)
                        Text("目标距离")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(AppTheme.onSurface)
                    }
                    DistanceSlider(
                        distanceKm: distanceKm,
                        range: AppConfig.minDistanceKm...AppConfig.maxDistanceKm
                    ) { value in
                        distanceKm = value
                    }
                }
            }
        }
    }

    // MARK: - 任务日志

    private var logsTab: some View {
        VStack(spacing: 14) {
            SemesterCalendar(loggedIn: viewModel.loggedIn, weeks: viewModel.semester.weeks)
            logSection
        }
    }

    private var logSection: some View {
        SectionCard(
            title: "运行日志",
            icon: "terminal",
            supporting: viewModel.running ? "任务运行中" : "共 \(viewModel.logs.count) 条记录",
            action: {
                if !viewModel.running && !viewModel.logs.isEmpty {
                    Button {
                        viewModel.clearLogs()
                    } label: {
                        Text("清空")
                    }
                    .buttonStyle(.glass)
                }
            }
        ) {
            ConsoleLog(entries: viewModel.logs)
                .frame(maxWidth: .infinity)
                .frame(height: logHeight)
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.panelCornerRadius))
        }
    }

    // MARK: - 底部操作栏与标签栏

    @ViewBuilder
    private var bottomArea: some View {
        VStack(spacing: 10) {
            if tab == 0 {
                actionBar
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            } else if viewModel.running {
                // 其他页面只留一条紧凑状态栏，不再占用整条底边。
                compactRunningBar
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }

            LiquidTabBar(selection: $tab, items: navTabs)
        }
        .frame(maxWidth: 560)
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 6)
        .animation(.snappy(duration: 0.32, extraBounce: 0.06), value: viewModel.running)
    }

    private var actionBar: some View {
        HStack(spacing: 10) {
            Button {
                withAnimation(.snappy(duration: 0.34, extraBounce: 0.08)) {
                    tab = 1
                }
                viewModel.previewRoute()
            } label: {
                Image(systemName: "map")
                    .font(.system(size: 17, weight: .semibold))
                    .frame(width: 50, height: 50)
            }
            .buttonStyle(.glass)
            .disabled(viewModel.running)
            .accessibilityLabel("预览路线")

            if viewModel.running {
                Button {
                    viewModel.stopUpload()
                } label: {
                    actionLabel(
                        title: "停止任务",
                        icon: "stop.fill"
                    )
                }
                .buttonStyle(.glassProminent)
                .tint(AppTheme.error)
            } else {
                Button {
                    viewModel.startUpload(config)
                } label: {
                    actionLabel(
                        title: "开始任务",
                        icon: "play.fill"
                    )
                }
                .buttonStyle(.glassProminent)
                .disabled(viewModel.selectedRoute == nil)
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func actionLabel(title: String, icon: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 16, weight: .bold))
            Text(title)
                .font(.subheadline.weight(.semibold))
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 16)
        .frame(maxWidth: .infinity, minHeight: 50)
    }

    private var compactRunningBar: some View {
        HStack(spacing: 10) {
            ZStack {
                Circle()
                    .stroke(AppTheme.onSurfaceVariant.opacity(0.22), lineWidth: 3)
                Circle()
                    .trim(from: 0, to: max(viewModel.progress.fraction, 0.03))
                    .stroke(AppTheme.error, style: StrokeStyle(lineWidth: 3, lineCap: .round))
                    .rotationEffect(.degrees(-90))
            }
            .frame(width: 20, height: 20)

            VStack(alignment: .leading, spacing: 1) {
                Text(viewModel.progress.status.label)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.onSurface)
                Text("\(viewModel.progress.current)/\(viewModel.progress.total) 次")
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(AppTheme.onSurfaceVariant)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Button(role: .destructive) {
                viewModel.stopUpload()
            } label: {
                Label("停止", systemImage: "stop.fill")
                    .font(.caption.weight(.semibold))
            }
            .buttonStyle(.glass)
            .tint(AppTheme.error)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
        .glassEffect(.regular.tint(AppTheme.error.opacity(0.10)), in: Capsule())
    }

    // MARK: - 浮层提示

    @ViewBuilder
    private var noticeLayer: some View {
        VStack(spacing: 0) {
            NoticeOverlay(notice: viewModel.notice)
                .padding(.horizontal, 16)
                .padding(.top, 6)
            Spacer(minLength: 0)
        }
        .allowsHitTesting(false)
        // 浮层提示 5 秒后自动收起，和电脑版一样不再往下推内容。
        .task(id: viewModel.notice?.id) {
            guard viewModel.notice != nil else { return }
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            withAnimation { viewModel.clearNotice() }
        }
    }

    // MARK: - 弹窗

    @ViewBuilder
    private var dialogLayer: some View {
        if showCommitment {
            CommitmentDialog(
                onAccept: {
                    commitmentAccepted = true
                    showCommitment = false
                },
                onDecline: {
                    // 对齐安卓：拒绝承诺书则退出程序
                    exit(0)
                }
            )
            .zIndex(1)
        }

        if let conflict = viewModel.routeConflict {
            RouteConflictDialog(conflict: conflict) { decision in
                viewModel.resolveRouteConflict(decision)
            }
            .zIndex(2)
        }

        if let route = routeToDelete {
            deleteRouteDialog(route)
                .zIndex(4)
        }
    }

    private func deleteRouteDialog(_ route: RouteInfo) -> some View {
        DialogScrim(onTapOutside: { routeToDelete = nil }) {
            VStack(alignment: .leading, spacing: 16) {
                Text("删除路线")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(AppTheme.onSurface)
                Text("确定要删除路线「\(route.name)」吗？该操作不可撤销。")
                    .font(.callout)
                    .foregroundStyle(AppTheme.onSurfaceVariant)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: 10) {
                    Button {
                        routeToDelete = nil
                    } label: {
                        Text("取消").frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.glass)

                    Button {
                        viewModel.deleteRoute(route)
                        routeToDelete = nil
                    } label: {
                        Text("删除").frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.glassProminent)
                    .tint(AppTheme.error)
                }
            }
        }
    }
}

// MARK: - 日期选择

struct DatePickerSheet: View {
    @Binding var date: Date
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            DatePicker("选择日期", selection: $date, displayedComponents: .date)
                .datePickerStyle(.graphical)
                .padding()
                .navigationTitle("结束日期")
                #if os(iOS)
                .navigationBarTitleDisplayMode(.inline)
                #endif
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("确定") { dismiss() }
                    }
                }
        }
    }
}
