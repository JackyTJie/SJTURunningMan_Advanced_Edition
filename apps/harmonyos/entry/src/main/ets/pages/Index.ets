import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { promptAction } from '@kit.ArkUI';
import { preferences } from '@kit.ArkData';
import { RunScreen } from '../view/RunScreen';
import { LoginPage } from '../pages/Login';
import { RouteDesignPage } from '../pages/RouteDesign';
import { AboutPage } from '../pages/About';
import { SemesterPage } from '../pages/Semester';
import { MainViewModel } from '../viewmodel/MainViewModel';
import { LogLevel } from '../viewmodel/TaskModels';
import { AppConfig } from '../config/AppConfig';
import { CookieService } from '../service/CookieService';
import { APP_HEADER_HEIGHT } from '../view/CommonComponents';

const DOMAIN: number = 0x0000;
const TAG: string = 'IndexPage';
const PREFS_NAME: string = 'app_prefs';
const PREF_COMMITMENT_ACCEPTED: string = 'commitment_accepted';

/**
 * 根界面
 * 迁移自 Android: com.sjtu.runner.MainActivity + MainScreen.kt 中的 RootScreen
 *
 * - Activity -> @Entry 页面（Stage 模型）
 * - 右上角菜单 -> 本页自绘标题栏（TitleBar Builder）里的“账号/登录”与“关于”图标按钮，
 *   等价 Android CenterAlignedTopAppBar 的 action 槽位；标题与按钮同一行
 * - 二级页面（登录/路线设计/学期日历/关于）-> 原生 Navigation + NavDestination + NavPathStack，
 *   由系统提供标题栏与返回控件（等价 Android startActivity/startActivityForResult）
 * - 使用承诺书门禁：与安卓一致，未同意时以全屏卡片遮挡并允许“退出”结束应用
 *
 * 说明：此前用 HdsTabs 悬浮页签承载“开润/账号”，现按需求取消底部页签，
 * 账号入口（登录状态/退出登录）与“关于”统一收进标题栏右上角图标按钮。
 *
 * 关于 HDS / 沉浸光感：旧实现用 UI Design Kit 的 HdsNavigation + hdsMaterial 渲染
 * 沉浸光感标题栏，但该 Kit（连同 ArkUI 的 uiMaterial.ImmersiveMaterial）只在更晚的
 * SDK 里才有；本工程按 API 21（HarmonyOS 6.0.1）构建，故改用原生 Navigation + 自绘标题栏，
 * 视觉降级为普通的实色标题栏与卡片。要恢复沉浸光感需升级 DevEco Studio / SDK 到含
 * UIDesignKit 的版本，并用 'x.y.z(API级别)' 形式回写 compileSdkVersion。
 */
@Entry
@Component
struct Index {
  private viewModel: MainViewModel = MainViewModel.getInstance();
  /** 主导航栈：登录 / 路线设计 / 关于 二级页均挂载于此 */
  private pathStack: NavPathStack = new NavPathStack();

  /** 使用承诺书是否已同意（持久化于 app_prefs/commitment_accepted；读取失败时保持未同意） */
  @State commitmentAccepted: boolean = false;
  /** 承诺书勾选状态（等价 Android MainScreen 的 commitmentChecked） */
  @State commitmentChecked: boolean = false;

  aboutToAppear(): void {
    // 触发重新登录回调：清理 cookie 并跳转登录页（等价 MainActivity.onReloginRequired）
    this.viewModel.onReloginRequired = () => {
      this.viewModel.logMsg(LogLevel.WARN, '检测到cookie过期，正在重新登录...');
      this.pathStack.pushPathByName('Login', null);
    };

    // 初始化 ViewModel 与路线列表
    const context = getContext(this) as common.UIAbilityContext;
    this.viewModel.init(context);
    // 启动时同步一次登录态（cookie 由系统 WebView cookie jar 持久化，
    // 等价 Android 启动时读 CookieManager 判断是否已登录）
    this.viewModel.refreshLoginState();

    // 检查使用承诺书是否已同意（等价 MainActivity.onCreate 中的 SharedPreferences 检查）
    // 读取失败时保持“未同意”，与 Android prefs.getBoolean(KEY, false) 的 fail-closed 语义一致
    try {
      const prefs = preferences.getPreferencesSync(context, { name: PREFS_NAME });
      this.commitmentAccepted = prefs.getSync(PREF_COMMITMENT_ACCEPTED, false) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, 'read commitment flag failed: %{public}s', JSON.stringify(e));
      this.commitmentAccepted = false;
    }
  }

  /** 持久化承诺书同意标记 */
  private acceptCommitment(): void {
    try {
      const context = getContext(this) as common.UIAbilityContext;
      const prefs = preferences.getPreferencesSync(context, { name: PREFS_NAME });
      prefs.putSync(PREF_COMMITMENT_ACCEPTED, true);
      prefs.flushSync();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, 'persist commitment flag failed: %{public}s', JSON.stringify(e));
    }
    this.commitmentChecked = false;
    this.commitmentAccepted = true;
  }

  /** 拒绝承诺书：退出应用（等价 Android Activity.finish()） */
  private declineCommitment(): void {
    (getContext(this) as common.UIAbilityContext).terminateSelf();
  }

  /**
   * 使用承诺书门禁（等价 Android CommitmentDialog）。
   * 覆盖在整个 Navigation 之上（含自绘标题栏），未同意时无法操作其它界面；
   * Android 用 AlertDialog + 复选框，ArkUI 的 AlertDialog 不支持自定义内容组件，故用全屏遮罩实现。
   */
  @Builder
  CommitmentDialog() {
    Column() {
      Column({ space: 14 }) {
        Text('使用承诺书')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor($r('app.color.text_primary'))
          .width('100%')

        Scroll() {
          Text(AppConfig.COMMITMENT_TEXT)
            .fontSize(14)
            .lineHeight(22)
            .fontColor($r('app.color.text_primary'))
            .width('100%')
        }
        .scrollable(ScrollDirection.Vertical)
        .scrollBar(BarState.Auto)
        .width('100%')
        .constraintSize({ maxHeight: 300 })
        .align(Alignment.TopStart)

        Row({ space: 8 }) {
          Checkbox()
            .select(this.commitmentChecked)
            .selectedColor($r('app.color.brand_primary'))
            .onChange((value: boolean) => {
              this.commitmentChecked = value;
            })
          Text('我已阅读以上内容，并承诺不会将本软件用于任何违规操作。')
            .fontSize(14)
            .fontColor($r('app.color.text_primary'))
            .layoutWeight(1)
        }
        .width('100%')
        .alignItems(VerticalAlign.Top)

        Row({ space: 10 }) {
          Button('退出')
            .fontSize(15)
            .height(44)
            .layoutWeight(1)
            .borderRadius(22)
            .backgroundColor(Color.Transparent)
            .fontColor($r('app.color.error_color'))
            .onClick(() => {
              this.declineCommitment();
            })
          Button('我承诺，进入软件')
            .fontSize(15)
            .height(44)
            .layoutWeight(1)
            .borderRadius(22)
            .backgroundColor($r('app.color.brand_primary'))
            .fontColor($r('app.color.text_on_brand'))
            .enabled(this.commitmentChecked)
            .opacity(this.commitmentChecked ? 1 : 0.5)
            .onClick(() => {
              this.acceptCommitment();
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

  /** 账号/登录入口：已登录弹出“退出账号”确认，未登录跳转 JAccount 登录页 */
  private onAccountEntry(): void {
    this.viewModel.refreshLoginState();
    if (!this.viewModel.loginState) {
      this.pathStack.pushPathByName('Login', null);
      return;
    }
    AlertDialog.show({
      title: '退出账号',
      message: '是否退出该账号？',
      autoCancel: true,
      alignment: DialogAlignment.Center,
      primaryButton: {
        value: '取消',
        action: () => {
        }
      },
      secondaryButton: {
        value: '退出',
        fontColor: $r('app.color.error_color'),
        action: () => {
          this.handleLogout();
        }
      }
    });
  }

  /** 退出登录：清理 cookie 与登录状态（等价 Android AccountScreen.handleLogout） */
  private handleLogout(): void {
    CookieService.clearAll();
    this.viewModel.loginState = false;
    this.viewModel.reloginRequired = false;
    // 退出账号后学期进度与日历不能留着上一个账号的数据
    this.viewModel.clearSemesterView();
    promptAction.showToast({ message: '已退出登录', duration: 1500 });
  }

  /** 标题栏右侧图标按钮（等价 Android TopAppBar 的 action） */
  @Builder
  ActionIcon(symbol: Resource, label: string, onTap: () => void) {
    Button() {
      SymbolGlyph(symbol)
        .fontSize(22)
        .fontColor([$r('app.color.text_primary')])
    }
    .type(ButtonType.Circle)
    .width(44)
    .height(44)
    .backgroundColor(Color.Transparent)
    .accessibilityText(label)
    .onClick(() => {
      onTap();
    })
  }

  /**
   * 顶部标题栏：标题与右上角两个图标按钮同一行（原本由 HDS MINI 标题模式提供）。
   * 它是布局中的实体节点（AppHeader 高度 APP_HEADER_HEIGHT），不是悬浮层。
   */
  @Builder
  TitleBar() {
    Row({ space: 4 }) {
      Text('开润')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .fontColor($r('app.color.text_primary'))
        .layoutWeight(1)
        .textAlign(TextAlign.Start)
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })

      this.ActionIcon(
        $r('sys.symbol.calendar'),
        '学期日历',
        (): void => {
          this.pathStack.pushPathByName('Semester', null);
        }
      )
      this.ActionIcon(
        $r('sys.symbol.person_crop_circle_fill_1'),
        this.viewModel.loginState ? '账号' : '登录',
        (): void => {
          this.onAccountEntry();
        }
      )
      this.ActionIcon(
        $r('sys.symbol.info_circle'),
        '关于',
        (): void => {
          this.pathStack.pushPathByName('About', null);
        }
      )
    }
    .width('100%')
    .height(APP_HEADER_HEIGHT)
    .padding({ left: 16, right: 8 })
    .alignItems(VerticalAlign.Center)
    .backgroundColor($r('app.color.page_background'))
  }

  /** 二级页路由表：登录 / 路线设计 / 关于（系统标题栏 + 原生返回键） */
  @Builder
  PageMap(name: string) {
    if (name === 'Login') {
      LoginPage({ navStack: this.pathStack })
    } else if (name === 'RouteDesign') {
      RouteDesignPage({ navStack: this.pathStack })
    } else if (name === 'About') {
      AboutPage()
    } else if (name === 'Semester') {
      SemesterPage()
    }
  }

  build() {
    // 单根容器 Stack：Navigation 与全屏承诺书遮罩是兄弟节点（等价 Android 中
    // CommitmentDialog 渲染在 Scaffold 之外，覆盖含顶栏的整屏）
    Stack() {
      Navigation(this.pathStack) {
        Column() {
          this.TitleBar()
          // 一级页内容占据标题栏之外的剩余高度（RunScreen 自身按 100% 高度布局）
          Column() {
            RunScreen({ navStack: this.pathStack })
          }
          .width('100%')
          .layoutWeight(1)
        }
        .width('100%')
        .height('100%')
        .alignItems(HorizontalAlign.Start)
      }
      .mode(NavigationMode.Stack)
      .navDestination(this.PageMap)
      // 标题栏由本页自绘（TitleBar），关闭 Navigation 自带标题栏避免出现两条
      .hideTitleBar(true)
      .hideToolBar(true)
      .width('100%')
      .height('100%')

      // ===== 使用承诺书门禁：作为 Stack 子节点覆盖整个 Navigation（含标题栏） =====
      if (!this.commitmentAccepted) {
        this.CommitmentDialog()
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor($r('app.color.page_background'))
  }
}
