/**
 * 学期日历页（二级页，挂载于 Index 的 Navigation 导航栈）
 * 迁移自 Android: com.sjtu.runner.ui.MainScreen 的 tab 2（SemesterCalendar + LogCard）
 *
 * 鸿蒙端把「运行日志」留在主页面上（与任务同屏更好用），本页只承载学期日历；
 * 「本学期进度」卡片在主页状态卡下方。数据都来自 MainViewModel.refreshSemesterStats()。
 */
import { SemesterCalendarCard } from '../view/SemesterViews';
import { MainViewModel } from '../viewmodel/MainViewModel';

@Component
export struct SemesterPage {
  private viewModel: MainViewModel = MainViewModel.getInstance();

  aboutToAppear(): void {
    // 每次进页面刷新一次：日历是只读展示，登录后应尽量看到最新打卡状态
    this.viewModel.refreshLoginState();
    if (this.viewModel.loginState) {
      this.viewModel.refreshSemesterStats();
    }
  }

  build() {
    NavDestination() {
      Scroll() {
        Column({ space: 14 }) {
          SemesterCalendarCard({
            loggedIn: this.viewModel.loginState,
            weeks: this.viewModel.semesterWeeks
          })
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 16, bottom: 32 })
      }
      .scrollable(ScrollDirection.Vertical)
      .scrollBar(BarState.Auto)
      .width('100%')
      .height('100%')
      .align(Alignment.Top)
    }
    .title('学期日历')
    .backgroundColor($r('app.color.page_background'))
  }
}
