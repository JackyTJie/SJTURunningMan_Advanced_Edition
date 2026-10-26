import { promptAction } from '@kit.ArkUI';
import { MainViewModel, RunConfig } from '../viewmodel/MainViewModel';
import { RouteConflict, RouteDecision, RoutePreview, TrackSample } from '../viewmodel/TaskModels';
import { RouteInfo } from '../model/RouteInfo';
import { SettingCard } from './CommonComponents';
import { DistanceSlider, MenuDropdown, MenuOption, NumberField, SectionDivider } from './Controls';
import { StatusCard, StatItem } from './StatusCard';
import { ConsoleLog } from './ConsoleLog';
import { SemesterProgressCard } from './SemesterViews';
import { RoutePreviewCanvas } from './RoutePreviewCanvas';
import { parseDate, yesterday, formatDate } from '../utils/FormatUtil';
import { AppConfig } from '../config/AppConfig';

/**
 * 主运行界面（第一个页签“开润”）
 * 迁移自 Android: com.sjtu.runner.ui.MainScreen @Composable
 *
 * 布局与交互与安卓版保持一致（自上而下）：
 * 状态卡 -> 重新登录提示 -> 跑步路线（预设路线/预览画布/预览/删除）
 * -> 任务设置（跑步次数/开始时间/结束日期/目标距离）
 * -> 运行日志（等级着色 + 清空） -> 免责提示 -> 底部操作栏（预览/开始/停止）
 *
 * ArkUI 差异说明：
 * - 安卓 TopAppBar 的两个 action（关于/重新登录）改为页签容器的标题栏与“关于”二级页承载；
 * - 安卓的底部 bottomBar 在本页以底部固定操作栏实现；
 * - 承诺书弹窗由 Index 页面承载（应用级门禁），本页只管任务。
 */

/** 跑步次数下拉框的常用档位（等价安卓预设 chip） */
const COMMON_DAYS: number[] = [1, 3, 5, 7, 10, 15, 30];
/** 跑步次数下拉框里「自定义…」项的 key */
const CUSTOM_DAYS_KEY: string = '__custom_days__';
/** 任务设置行内下拉框宽度（vp） */
const SETTING_DROPDOWN_WIDTH: number = 120;

@Component
export struct RunScreen {
  viewModel: MainViewModel = MainViewModel.getInstance();
  /** 主导航栈（由 Index 传入），用于跳转登录页/路线设计页 */
  navStack: NavPathStack = new NavPathStack();

  // ===== 任务设置状态（等价 Android MainScreen 的 remember 变量） =====
  @State days: number = 1;
  @State distanceKm: number = AppConfig.DEFAULT_DISTANCE_KM;
  @State timeHour: number = AppConfig.DEFAULT_RUN_HOUR;
  @State timeMinute: number = AppConfig.DEFAULT_RUN_MINUTE;
  @State timeSecond: number = AppConfig.DEFAULT_RUN_SECOND;
  @State dateText: string = formatDate(yesterday());
  @State customDaysText: string = '';
  @State showCustomDays: boolean = false;
  /** 防止同一次路线冲突重复弹窗（等价 Android 的 routeConflict 一次性消费） */
  @State conflictShown: boolean = false;
  /** 路线距离提醒弹窗可见性（ArkUI AlertDialog 只有两个按钮，无法承载 Android 的三个选项） */
  @State conflictDialogVisible: boolean = false;
  /** 是否跳过已有记录的日期（数据源在 ViewModel，这里保留一份供开关渲染与点击后立即刷新） */
  @State skipExisting: boolean = true;
  /**
   * 使用承诺书门禁由 Index 页面以全屏遮罩实现（等价 Android CommitmentDialog）。
   * Android 把门禁渲染在 Scaffold 之外，因此必须由根页面承载；放在本组件内会只遮住 Tab 内容区，
   * 顶部标题栏与悬浮页签仍可点击，门禁形同虚设。
   */

  aboutToAppear(): void {
    this.viewModel.refreshLoginState();
    this.viewModel.updateConfig(this.buildConfig());
    // 目标距离读数写在 SettingCard 标签行，值从 AppStorage 读取；这里写入初值
    AppStorage.setOrCreate('distanceKmText', `${this.distanceKm.toFixed(1)} km`);
    // 路线冲突由 ViewModel 挂起任务时回调（等价 Compose 对 routeConflict 状态的响应）
    this.viewModel.onRouteConflict = (): void => {
      this.showConflictIfNeeded();
    };
    this.showConflictIfNeeded();
    // 「跳过已有记录的日期」持久化在 ViewModel 里，首次进入时取回
    this.skipExisting = this.viewModel.skipExisting;
    // 自动排计划生效后把输入控件对齐（等价 MainScreen 的 LaunchedEffect(autoPlanApplied)）
    this.viewModel.onAutoPlanApplied = (runs: number, distanceKm: number): void => {
      this.applyAutoPlan(runs, distanceKm);
    };
    // ViewModel 的 notify() 在安卓上同时弹浮层与写日志，这里用 toast 承担浮层
    this.viewModel.onNotice = (message: string): void => {
      promptAction.showToast({ message: message, duration: 3000 });
    };
    const restored = this.viewModel.autoPlanApplied;
    if (restored !== undefined) {
      this.applyAutoPlan(restored.runs, restored.distanceKm);
    }
  }

  private showConflictIfNeeded(): void {
    const conflict = this.viewModel.routeConflict;
    if (conflict === undefined) {
      this.conflictShown = false;
      return;
    }
    if (this.conflictShown) {
      return;
    }
    this.conflictShown = true;
    this.conflictDialogVisible = true;
  }

  /** 关闭路线距离提醒并把用户选择交给 ViewModel */
  private resolveConflict(decision: RouteDecision): void {
    this.conflictDialogVisible = false;
    this.viewModel.resolveRouteConflict(decision);
  }

  // ==================== 配置 ====================

  /** 由界面状态构造任务配置（等价 Android MainScreen 的 config remember） */
  private buildConfig(): RunConfig {
    const parsed = parseDate(this.dateText);
    const startDate = parsed !== null ? parsed : yesterday();
    return new RunConfig(this.days, this.distanceKm, this.timeHour, this.timeMinute, this.timeSecond, startDate,
      undefined);
  }

  /** 把自动排计划的「次数 × 单次距离」写回输入控件 */
  private applyAutoPlan(runs: number, distanceKm: number): void {
    this.days = runs;
    this.showCustomDays = false;
    this.distanceKm = distanceKm;
    AppStorage.setOrCreate('distanceKmText', `${distanceKm.toFixed(1)} km`);
    // 提示文案由 ViewModel 的 notify() 经 onNotice 弹出，这里只回填参数
    this.viewModel.updateConfig(this.buildConfig());
  }

  // ==================== 卡片选项 ====================

  /**
   * 目标距离滑杆（SettingCard 控件列内容）。
   *
   * 必须在 @Builder 方法里调用自定义组件：直接把 `DistanceSlider({...})` 写在
   * 传给组件的箭头函数里，ArkTS 编译器不会把该调用重写成
   * `new DistanceSlider(this, {...})`，运行时会抛出
   * `TypeError: class constructor cannot called without 'new'`（真机 nova 12 Ultra 崩溃）。
   */
  @Builder
  DistanceSliderBuilder() {
    DistanceSlider({
      // 单向绑定：父组件是唯一数据源，滑杆通过 onDistanceChange 上报新值
      distanceKm: this.distanceKm,
      minDistanceKm: AppConfig.MIN_DISTANCE_KM,
      maxDistanceKm: AppConfig.MAX_DISTANCE_KM,
      isEnabled: !this.viewModel.running,
      // 读数已渲染在标签行，滑杆只画轨道 + 右侧上限
      showValueRow: false,
      onDistanceChange: (value: number): void => {
        this.distanceKm = value;
        // 标签行读数从 AppStorage 读取（父组件 @State 写入不会触发卡片重建）
        AppStorage.setOrCreate('distanceKmText', `${value.toFixed(1)} km`);
        this.viewModel.updateConfig(this.buildConfig());
      }
    })
  }

  private pickDate(): void {
    const selected = parseDate(this.dateText);
    DatePickerDialog.show({
      start: new Date(2000, 0, 1),
      end: new Date(2100, 0, 1),
      selected: selected !== null ? selected : yesterday(),
      onDateAccept: (value: Date): void => {
        this.dateText = formatDate(value);
        this.viewModel.updateConfig(this.buildConfig());
      }
    });
  }

  // ==================== 运行日志 ====================

  private stats(): StatItem[] {
    const result: StatItem[] = [];
    result.push(new StatItem('次数', `${this.days}`));
    result.push(new StatItem('距离', `${this.distanceKm.toFixed(1)} km`));
    result.push(new StatItem('时间',
      `${pad(this.timeHour)}:${pad(this.timeMinute)}:${pad(this.timeSecond)}`));
    return result;
  }

  // ==================== 预览 / 删除 ====================

  private routePreview(): RoutePreview | undefined {
    return this.viewModel.preview;
  }

  private previewSamples(): TrackSample[] {
    const preview = this.viewModel.preview;
    return preview !== undefined ? preview.samples : [];
  }

  private previewJumpCount(): number {
    const preview = this.viewModel.preview;
    return preview !== undefined ? preview.jumpCount : 0;
  }

  private deleteCurrentRoute(): void {
    const route = this.viewModel.selectedRoute;
    if (route === undefined || route.isDefault || this.viewModel.running) {
      return;
    }
    const target: RouteInfo = route;
    AlertDialog.show({
      title: '删除路线',
      message: `确定要删除路线「${target.name}」吗？该操作不可撤销。`,
      autoCancel: true,
      alignment: DialogAlignment.Center,
      primaryButton: {
        value: '取消',
        action: () => {
        }
      },
      secondaryButton: {
        value: '删除',
        fontColor: $r('app.color.error_color'),
        action: () => {
          this.viewModel.deleteRoute(target);
        }
      }
    });
  }

  // ==================== 路线距离提醒 ====================

  /** 路线长度超过目标距离时弹出三选一（等价 Android RouteConflictDialog） */
  @Builder
  RouteConflictDialog() {
    Column() {
      Column({ space: 12 }) {
        Text('路线距离提醒')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor($r('app.color.text_primary'))
          .width('100%')

        Text(`当前路线「${this.viewModel.routeConflict?.routeName ?? ''}」长度为 `
          + `${((this.viewModel.routeConflict?.routeDistanceM ?? 0) / 1000.0).toFixed(2)}km，`
          + `超过了您选择的 ${((this.viewModel.routeConflict?.targetDistanceM ?? 0) / 1000.0).toFixed(2)}km。`)
          .fontSize(14)
          .lineHeight(22)
          .fontColor($r('app.color.text_primary'))
          .width('100%')

        Text('削减：自动截断路线至目标距离')
          .fontSize(13)
          .lineHeight(20)
          .fontColor($r('app.color.text_secondary'))
          .width('100%')

        Text('完整路线：按整条路线跑步并同步目标距离')
          .fontSize(13)
          .lineHeight(20)
          .fontColor($r('app.color.text_secondary'))
          .width('100%')

        Row({ space: 10 }) {
          Button('削减路线')
            .fontSize(14)
            .height(44)
            .layoutWeight(1)
            .borderRadius(22)
            .backgroundColor($r('app.color.brand_primary'))
            .fontColor($r('app.color.text_on_brand'))
            .onClick(() => {
              this.resolveConflict(RouteDecision.TRUNCATE);
            })
          Button('取消任务')
            .fontSize(14)
            .height(44)
            .layoutWeight(1)
            .borderRadius(22)
            .backgroundColor(Color.Transparent)
            .fontColor($r('app.color.text_secondary'))
            .onClick(() => {
              this.resolveConflict(RouteDecision.CANCEL);
            })
          Button('完整路线')
            .fontSize(14)
            .height(44)
            .layoutWeight(1)
            .borderRadius(22)
            .backgroundColor(Color.Transparent)
            .fontColor($r('app.color.brand_primary'))
            .border({ width: 1, color: $r('app.color.brand_primary') })
            .onClick(() => {
              this.resolveConflict(RouteDecision.FULL_ROUTE);
            })
        }
        .width('100%')
      }
      .width('90%')
      .padding(20)
      .borderRadius(24)
      .backgroundColor($r('app.color.card_surface'))
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#99000000')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }

  // ==================== 子构件 ====================

  /** 「跳过已有记录的日期」开关（等价 Android SkipExistingRow，成功色底衬） */
  @Builder
  SkipExistingRow() {
    Row({ space: 4 }) {
      Checkbox()
        .select(this.skipExisting)
        .selectedColor($r('app.color.success_color'))
        .enabled(!this.viewModel.running)
        .onChange((value: boolean): void => {
          this.skipExisting = value;
          this.viewModel.setSkipExisting(value);
        })
      Column({ space: 2 }) {
        Text('跳过已有记录的日期')
          .fontSize(13)
          .fontColor($r('app.color.text_primary'))
        Text('已有记录的那几天挪到更早日期。')
          .fontSize(11)
          .fontColor($r('app.color.text_secondary'))
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start)
    }
    .width('100%')
    .padding({ left: 4, right: 14, top: 2, bottom: 2 })
    .borderRadius(14)
    .backgroundColor($r('app.color.success_container'))
    .alignItems(VerticalAlign.Center)
  }

  @Builder
  DaysSelector() {
    Row({ space: 8 }) {
      // 常用次数用系统下拉框（Select）选择；「自定义…」切到数字输入框。
      // 选自定义后下拉框自身要显示「自定义」，否则框里仍是旧数字、与右侧输入框对不上。
      MenuDropdown({
        value: this.showCustomDays ? '自定义' : `${this.days}`,
        options: this.dayMenuOptions(),
        isEnabled: !this.viewModel.running,
        onSelect: (key: string): void => {
          if (key === CUSTOM_DAYS_KEY) {
            this.showCustomDays = true;
            this.customDaysText = `${this.days}`;
            return;
          }
          this.showCustomDays = false;
          this.days = Number.parseInt(key, 10);
          this.viewModel.updateConfig(this.buildConfig());
        }
      })
      .width(SETTING_DROPDOWN_WIDTH)

      if (this.showCustomDays) {
        NumberField({
          value: this.days,
          label: '次数 1-30',
          maxLength: 2,
          fieldWidth: 96,
          isEnabled: !this.viewModel.running,
          onValueChange: (value: number): void => {
            this.customDaysText = `${value}`;
          }
        })
      }

      // 只在自定义输入态显示「确定」；否则会与下拉框并排多出一个空按钮。
      if (this.showCustomDays) {
        Button('确定')
          .fontSize(13)
          .height(34)
          .borderRadius(17)
          .backgroundColor($r('app.color.brand_primary'))
          .enabled(!this.viewModel.running)
          .onClick(() => {
            const n = Number.parseInt(this.customDaysText, 10);
            this.days = Number.isNaN(n) ? 1 : Math.max(1, Math.min(AppConfig.MAX_RUN_TIMES, n));
            this.showCustomDays = false;
            this.viewModel.updateConfig(this.buildConfig());
          })
      }
    }
    .alignItems(VerticalAlign.Bottom)
  }

  /** 常用次数下拉项；当前次数不在常用值里时，把它的 subtitle 设为「当前」以便选中项显示为自定义值 */
  private dayMenuOptions(): MenuOption[] {
    const options: MenuOption[] = [];
    for (let i = 0; i < COMMON_DAYS.length; i++) {
      const value = COMMON_DAYS[i];
      options.push(new MenuOption(`${value}`, `${value} 次`, '', this.days === value));
    }
    options.push(new MenuOption(CUSTOM_DAYS_KEY, '自定义…', '手动输入 1-30 之间的次数', this.showCustomDays));
    return options;
  }

  @Builder
  TimeSelector() {
    // 点按弹出系统 TimePickerDialog（24 小时制、时/分/秒）。
    // 不用内联 TimePicker：内联选择器竖排滚动、行高固定，卡片会多占约 200vp，
    // 且用户改一次时间要点三次（时/分/秒各滑一次）；弹窗方式与「结束日期」的
    // DatePickerDialog 保持一致，也符合系统应用的交互习惯。
    // 随机波动说明已折叠为标签旁的「圈 i」（SettingCard 的 infoText），
    // 因此这里只留控件本身，卡片高度回到与其它行一致。
    Row({ space: 6 }) {
      Text(this.timeText())
        .fontSize(16)
        .fontWeight(FontWeight.Medium)
        .fontColor($r('app.color.text_primary'))
      SymbolGlyph($r('sys.symbol.chevron_down'))
        .fontSize(14)
        .fontColor([$r('app.color.text_secondary')])
    }
    .padding({ left: 14, right: 12 })
    .height(38)
    .borderRadius(19)
    .backgroundColor($r('app.color.card_surface'))
    .border({ width: 1, color: $r('app.color.outline_variant') })
    .opacity(this.viewModel.running ? 0.5 : 1)
    .onClick(() => {
      if (!this.viewModel.running) {
        this.pickTime();
      }
    })
  }

  /** 弹出系统时间选择器（24 小时制、时/分/秒） */
  private pickTime(): void {
    // TimePickerFormat / TimePickerResult 是组件模块的全局类型（与 SelectOption 同理），
    // 未从 @kit.ArkUI 导出，无需也不能显式 import。
    const selected = new Date(2026, 0, 1, this.timeHour, this.timeMinute, this.timeSecond);
    TimePickerDialog.show({
      selected: selected,
      format: TimePickerFormat.HOUR_MINUTE_SECOND,
      useMilitaryTime: true,
      onAccept: (value: TimePickerResult): void => {
        if (value.second === undefined) {
          return;
        }
        this.timeHour = value.hour;
        this.timeMinute = value.minute;
        this.timeSecond = value.second;
        this.viewModel.updateConfig(this.buildConfig());
      }
    });
  }

  /** 开始时间展示文案（HH:MM:SS） */
  private timeText(): string {
    return `${pad(this.timeHour)}:${pad(this.timeMinute)}:${pad(this.timeSecond)}`;
  }

  @Builder
  RouteSelector() {
    MenuDropdown({
      label: '预设路线',
      value: this.viewModel.selectedRoute !== undefined ? this.viewModel.selectedRoute.name : '请选择路线',
      options: this.routeMenuOptions(),
      isEnabled: !this.viewModel.running,
      onSelect: (key: string): void => {
        if (key === '__new__') {
          this.navStack.pushPathByName('RouteDesign', null);
          return;
        }
        const routes = this.viewModel.routes;
        for (let i = 0; i < routes.length; i++) {
          if (routes[i].id === key) {
            this.viewModel.selectRoute(routes[i]);
            return;
          }
        }
      }
    })
  }

  private routeMenuOptions(): MenuOption[] {
    const options: MenuOption[] = [];
    const routes = this.viewModel.routes;
    const selectedId = this.viewModel.selectedRoute !== undefined ? this.viewModel.selectedRoute.id : '';
    for (let i = 0; i < routes.length; i++) {
      const route = routes[i];
      const subtitle = `${route.pointCount} 个点${route.isDefault ? ' · 内置' : ''}`;
      options.push(new MenuOption(route.id, route.name, subtitle, route.id === selectedId));
    }
    options.push(new MenuOption('__new__', '设计新路线', '在地图上点击采集坐标点', false));
    return options;
  }

  @Builder
  ReloginBanner() {
    Column({ space: 6 }) {
      Row({ space: 8 }) {
        SymbolGlyph($r('sys.symbol.exclamationmark_triangle_fill'))
          .fontSize(18)
          .fontColor([$r('app.color.error_color')])
        Text('Cookie 已过期')
          .fontSize(15)
          .fontWeight(FontWeight.Medium)
          .fontColor($r('app.color.text_primary'))
      }
      .alignItems(VerticalAlign.Center)

      Text('登录状态失效，请重新登录后继续上传。')
        .fontSize(14)
        .fontColor($r('app.color.text_secondary'))
        .width('100%')

      Button('登录')
        .fontSize(14)
        .height(36)
        .borderRadius(18)
        .backgroundColor($r('app.color.brand_primary_container'))
        .fontColor($r('app.color.brand_on_primary_container'))
        .alignSelf(ItemAlign.Start)
        .onClick(() => {
          this.viewModel.reloginRequired = false;
          this.navStack.pushPathByName('Login', null);
        })
    }
    .width('100%')
    .padding(16)
    .borderRadius(16)
    .backgroundColor($r('app.color.error_container'))
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  RouteSection() {
    Column({ space: 12 }) {
      Row({ space: 10 }) {
        Text('跑步路线')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor($r('app.color.text_primary'))
          .layoutWeight(1)
        SymbolGlyph($r('sys.symbol.plus'))
          .fontSize(18)
          .fontColor([$r('app.color.brand_primary')])
          .onClick(() => {
            this.navStack.pushPathByName('RouteDesign', null);
          })
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      this.RouteSelector()

      // 路线预览画布（原始路线 / 离线预览 / 待上传 / 已上传）
      RoutePreviewCanvas({
        samples: this.previewSamples(),
        jumpCount: this.previewJumpCount(),
        canvasHeight: 150
      })

      Row({ space: 8 }) {
        Text(this.routePreview() !== undefined ? (this.routePreview() as RoutePreview).title : '路线预览')
          .fontSize(14)
          .fontWeight(FontWeight.Medium)
          .fontColor($r('app.color.text_primary'))
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        if (this.previewJumpCount() > 0) {
          Text(`${this.previewJumpCount()} 处跳段`)
            .fontSize(11)
            .fontWeight(FontWeight.Medium)
            .fontColor($r('app.color.error_color'))
            .backgroundColor($r('app.color.error_container'))
            .padding({ left: 8, right: 8, top: 3, bottom: 3 })
            .borderRadius(8)
        }
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      Text(this.routePreview() !== undefined ? (this.routePreview() as RoutePreview).summary
        : '点击「预览路线」按当前设置离线生成')
        .fontSize(12)
        .fontColor($r('app.color.text_secondary'))
        .width('100%')

      SectionDivider()

      Row({ space: 10 }) {
        Button('预览路线')
          .fontSize(14)
          .height(40)
          .layoutWeight(1)
          .borderRadius(12)
          .backgroundColor(Color.Transparent)
          .fontColor($r('app.color.brand_primary'))
          .border({ width: 1, color: $r('app.color.brand_primary') })
          .enabled(!this.viewModel.running && this.viewModel.selectedRoute !== undefined)
          .onClick(() => {
            this.viewModel.previewRoute();
          })
        Button('删除路线')
          .fontSize(14)
          .height(40)
          .layoutWeight(1)
          .borderRadius(12)
          .backgroundColor(Color.Transparent)
          .fontColor($r('app.color.error_color'))
          .border({ width: 1, color: $r('app.color.error_color') })
          .enabled(!this.viewModel.running && this.viewModel.selectedRoute !== undefined
            && !(this.viewModel.selectedRoute as RouteInfo).isDefault)
          .onClick(() => {
            this.deleteCurrentRoute();
          })
      }
      .width('100%')
    }
    .width('100%')
    .padding(16)
    .borderRadius(20)
    .backgroundColor($r('app.color.card_surface'))
    .border({ width: 1, color: $r('app.color.outline_variant') })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  LogSection() {
    Column({ space: 10 }) {
      Row({ space: 10 }) {
        Text('运行日志')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor($r('app.color.text_primary'))
        Text(this.viewModel.running ? '任务运行中' : `共 ${this.viewModel.logs.length} 条记录`)
          .fontSize(12)
          .fontColor($r('app.color.text_secondary'))
          .layoutWeight(1)
        if (!this.viewModel.running && this.viewModel.logs.length > 0) {
          Button('清空')
            .fontSize(13)
            .height(32)
            .borderRadius(16)
            .backgroundColor(Color.Transparent)
            .fontColor($r('app.color.brand_primary'))
            .onClick(() => {
              this.viewModel.clearLogs();
            })
        }
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      Column() {
        ConsoleLog({
          entries: this.viewModel.logs,
          panelHeight: 210,
          placeholder: '就绪。点击「开始任务」启动。'
        })
      }
      .width('100%')
      .borderRadius(14)
      // 系统材质降级方案：日志面板本身是半透明底色（log_panel_background），
      // 叠加原生背景模糊即可得到相近的磨砂效果（API 21 没有 uiMaterial.ImmersiveMaterial）
      .backgroundBlurStyle(BlurStyle.Thin)
    }
    .width('100%')
    .padding(16)
    .borderRadius(20)
    .backgroundColor($r('app.color.card_surface'))
    .border({ width: 1, color: $r('app.color.outline_variant') })
    .alignItems(HorizontalAlign.Start)
  }

  @Builder
  DisclaimerNotice() {
    Row({ space: 10 }) {
      SymbolGlyph($r('sys.symbol.exclamationmark_triangle_fill'))
        .fontSize(18)
        .fontColor([$r('app.color.warning_color')])
      Text('本项目仅供学习、研究和技术测试，请勿用于伪造运动数据或规避体育锻炼要求。')
        .fontSize(12)
        .lineHeight(18)
        .fontColor($r('app.color.text_primary'))
        .layoutWeight(1)
    }
    .width('100%')
    .padding({ left: 14, right: 14, top: 12, bottom: 12 })
    .borderRadius(14)
    .backgroundColor($r('app.color.warning_container'))
    .alignItems(VerticalAlign.Top)
  }

  @Builder
  BottomActionBar() {
    Row({ space: 10 }) {
      Button('预览')
        .fontSize(15)
        .height(52)
        .layoutWeight(9)
        .borderRadius(16)
        .backgroundColor($r('app.color.brand_primary_container'))
        .fontColor($r('app.color.brand_on_primary_container'))
        .enabled(!this.viewModel.running && this.viewModel.selectedRoute !== undefined)
        .onClick(() => {
          this.viewModel.previewRoute();
        })

      if (this.viewModel.running) {
        Button('停止任务')
          .fontSize(15)
          .fontWeight(FontWeight.Medium)
          .height(52)
          .layoutWeight(11)
          .borderRadius(16)
          .backgroundColor($r('app.color.error_color'))
          .fontColor($r('app.color.on_error_container'))
          .onClick(() => {
            this.viewModel.stopUpload();
          })
      } else {
        Button('开始任务')
          .fontSize(15)
          .fontWeight(FontWeight.Medium)
          .height(52)
          .layoutWeight(11)
          .borderRadius(16)
          .backgroundColor($r('app.color.brand_primary'))
          .fontColor($r('app.color.text_on_brand'))
          .enabled(this.viewModel.selectedRoute !== undefined)
          .onClick(() => {
            this.startTask();
          })
      }
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 10, bottom: 10 })
    .backgroundColor($r('app.color.page_background'))
  }

  private startTask(): void {
    const config = this.buildConfig();
    this.viewModel.updateConfig(config);
    const error = this.viewModel.validate(config);
    if (error !== undefined) {
      promptAction.showToast({ message: error, duration: 2000 });
      return;
    }
    if (!this.viewModel.loginState) {
      promptAction.showToast({ message: '请先登录！', duration: 1500 });
      return;
    }
    this.viewModel.startUpload(config);
  }

  /**
   * 使用承诺书门禁由 Index 页面以全屏遮罩实现（等价 Android CommitmentDialog）。
   * Android 把门禁渲染在 Scaffold 之外，因此必须由根页面承载；放在本组件内会只遮住 Tab 内容区，
   * 顶部标题栏与悬浮页签仍可点击，门禁形同虚设。
   */

  build() {
    // 外层 Stack 只用于承载路线距离提醒的全屏遮罩（被打开时同时盖住底部操作栏）。
    Stack() {
      // 根容器用 Column 而非 Stack：底部操作栏必须是滚动区的“兄弟节点”并占据自身高度，
      // 这样 Scroll 只能分到剩余空间（layoutWeight(1)）。之前用 Stack 悬浮覆盖时，
      // Stack 会把 Scroll 撑满，滚动内容长期被操作栏遮住，用户以为“按钮没置底”。
      Column() {
        Scroll() {
          Column({ space: 14 }) {
            // ===== 状态卡 =====
            StatusCard({
              progress: this.viewModel.progress,
              headline: `${this.days} 次 · ${this.distanceKm.toFixed(1)} km`,
              stats: this.stats()
            })

            // ===== 本学期进度（只读，登录状态下自动同步） =====
            SemesterProgressCard({
              loggedIn: this.viewModel.loginState,
              kmText: this.viewModel.semesterKmText,
              percentText: this.viewModel.semesterPercentText
            })

            // ===== 重新登录提示 =====
            if (this.viewModel.reloginRequired) {
              this.ReloginBanner()
            }

            // ===== 跑步路线 =====
            this.RouteSection()

            // ===== 任务设置 =====
            Column({ space: 8 }) {
              Text('任务设置')
                .fontSize(16)
                .fontWeight(FontWeight.Medium)
                .fontColor($r('app.color.text_primary'))
                .margin({ left: 4, bottom: 4 })
              // 任务设置四行统一用自绘 SettingCard：图标列/标签列宽度固定，
              // 各行图标与标签左边缘严格对齐；控件列由 ArkUI 正常测量（详见 CommonComponents.ets）。
              // 非 fullWidth 行的控件右对齐贴卡片右内边距。
              SettingCard({ label: '跑步次数', symbol: $r('sys.symbol.repeat') }) {
                this.DaysSelector()
              }
              SettingCard({
                label: '开始时间',
                symbol: $r('sys.symbol.clock'),
                // 随机波动规则原本是一行常驻小字，占版面且每行都要重复读；
                // 折叠成标签旁的「圈 i」，点按弹出全文。
                infoText: '每条记录的开始时间会在所选时间基础上随机加入 ±10 分钟 / ±30 秒的波动。'
              }) {
                this.TimeSelector()
              }
              SettingCard({
                label: '结束日期',
                symbol: $r('sys.symbol.calendar'),
                valueText: this.dateText
              })
                .onClick((): void => {
                  if (!this.viewModel.running) {
                    this.pickDate();
                  }
                })
              // 跳过已有记录的日期：与安卓版一致，位于日期之后、目标距离之前
              this.SkipExistingRow()
              SettingCard({
                label: '目标距离',
                symbol: $r('sys.symbol.figure_run'),
                fullWidth: true
              }) {
                this.DistanceSliderBuilder()
              }
            }
            .width('100%')

            // ===== 运行日志 =====
            this.LogSection()

            // ===== 免责提示 =====
            this.DisclaimerNotice()
          }
          .width('100%')
          // 三边内边距：标题栏由 Index 自绘、在布局流中占位（不再是覆盖内容的悬浮层），
          // 这里只需常规间距。bottom 同理：底部操作栏是兄弟节点、已占走自身高度。
          .padding({
            left: 16,
            right: 16,
            top: 16,
            bottom: 16
          })
        }
        .scrollable(ScrollDirection.Vertical)
        .scrollBar(BarState.Auto)
        .width('100%')
        .layoutWeight(1)

        // ===== 底部操作栏 =====
        // 紧贴窗口底部，只保留 8vp 与系统手势条的间距（Navigation 已把内容限制在安全区内）。
        Column() {
          this.BottomActionBar()
        }
        .width('100%')
        .padding({ bottom: 8 })
      }
      .width('100%')
      .height('100%')

      // ===== 路线距离提醒（三选一，全屏遮罩，覆盖底部操作栏） =====
      if (this.conflictDialogVisible) {
        this.RouteConflictDialog()
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor($r('app.color.page_background'))
  }
}

/** 两位补零（本地实现，避免与 FormatUtil.pad2 的 import 冲突） */
function pad(value: number): string {
  return value < 10 ? `0${value}` : `${value}`;
}
