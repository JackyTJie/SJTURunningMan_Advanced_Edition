/**
 * 学期相关卡片：「本学期进度」与「学期日历」
 * 迁移自 Android: com.sjtu.runner.ui.components.SemesterCard / SemesterCalendar
 *
 * 两处都与安卓版一致地保持只读：数据由 MainViewModel.refreshSemesterStats() 拉取，
 * 本文件只负责渲染，未登录时进度显示 `--`、日历显示占位月份。
 */
import { CalendarDay, CalendarWeek, DayState } from '../service/SemesterStats';

/** 周一为起点的星期表头 */
const WEEK_LABELS: string[] = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

/** 「本学期进度」卡片：达标公里与完成率两个只读指标 */
@Component
export struct SemesterProgressCard {
  /** 是否已登录（决定副标题文案） */
  @Prop loggedIn: boolean = false;
  /** 达标公里文本，如 `12.34 km`；缺失时 `--` */
  @Prop kmText: string = '--';
  /** 完成率文本，如 `45.6%`；缺失时 `--` */
  @Prop percentText: string = '--';

  @Builder
  Metric(label: string, value: string) {
    Column({ space: 2 }) {
      Text(label)
        .fontSize(11)
        .fontColor($r('app.color.text_secondary'))
      Text(value)
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
        .fontColor($r('app.color.brand_primary'))
        .maxLines(1)
    }
    .layoutWeight(1)
    .alignItems(HorizontalAlign.Start)
  }

  build() {
    Column({ space: 10 }) {
      Row({ space: 10 }) {
        SymbolGlyph($r('sys.symbol.figure_run'))
          .fontSize(18)
          .fontColor([$r('app.color.brand_primary')])
        Text('本学期进度')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor($r('app.color.text_primary'))
        Text(this.loggedIn ? '登录状态下自动同步，只读展示当前学期。' : '登录账号后自动同步本学期数据。')
          .fontSize(12)
          .fontColor($r('app.color.text_secondary'))
          .layoutWeight(1)
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      Divider()
        .color($r('app.color.outline_variant'))
        .margin({ top: 2, bottom: 2 })

      Row({ space: 14 }) {
        this.Metric('达标公里', this.kmText)
        this.Metric('完成率', this.percentText)
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
}

/**
 * 「学期日历」卡片：周一起始，逐月展开本学期每一天。
 * 实心绿 = 计入成绩，描边 = 有记录但未计入，灰 = 未跑，空白格 = 补齐或不在学期内。
 */
@Component
export struct SemesterCalendarCard {
  /** 是否已登录（决定副标题与空态文案） */
  @Prop loggedIn: boolean = false;
  /** 按周展开的日历行（每行 7 格） */
  @Prop weeks: CalendarWeek[] = [];

  @Builder
  DayCell(day: CalendarDay) {
    Column() {
      if (day.day > 0) {
        Text(`${day.day}`)
          .fontSize(11)
          .fontWeight(day.state === DayState.VALID ? FontWeight.Medium : FontWeight.Normal)
          .fontColor($r('app.color.calendar_ink'))
          .textAlign(TextAlign.Center)
          .width(24)
          .height(24)
          .borderRadius(12)
          .backgroundColor(this.cellBackground(day.state))
          .border({
            width: day.state === DayState.INVALID ? 1 : 0,
            color: $r('app.color.brand_primary')
          })
      }
    }
    .layoutWeight(1)
    .height(26)
    .justifyContent(FlexAlign.Center)
  }

  private cellBackground(state: DayState): ResourceColor {
    if (state === DayState.VALID) {
      return $r('app.color.run_valid');
    }
    if (state === DayState.INVALID) {
      return $r('app.color.run_invalid');
    }
    return $r('app.color.calendar_empty');
  }

  build() {
    Column({ space: 10 }) {
      Row({ space: 10 }) {
        SymbolGlyph($r('sys.symbol.calendar'))
          .fontSize(18)
          .fontColor([$r('app.color.brand_primary')])
        Text('学期日历')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor($r('app.color.text_primary'))
        Text(this.loggedIn ? '实心绿=计入成绩，描边=无效记录，灰=未跑。' : '登录后显示本学期打卡记录。')
          .fontSize(12)
          .fontColor($r('app.color.text_secondary'))
          .layoutWeight(1)
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      Divider()
        .color($r('app.color.outline_variant'))
        .margin({ top: 2, bottom: 2 })

      // 星期表头
      Row() {
        ForEach(WEEK_LABELS, (label: string) => {
          Text(label)
            .fontSize(11)
            .fontColor($r('app.color.text_secondary'))
            .textAlign(TextAlign.Center)
            .layoutWeight(1)
        }, (label: string) => label)
      }
      .width('100%')

      Column({ space: 2 }) {
        ForEach(this.weeks, (week: CalendarWeek, index: number) => {
          Column({ space: 2 }) {
            // 每月第一行带月份标题，其余行留空（高度一致，避免行距忽大忽小）
            Text(week.title)
              .fontSize(11)
              .fontColor($r('app.color.text_secondary'))
              .width('100%')
              .height(week.title.length > 0 ? 16 : 0)
            Row() {
              ForEach(week.days, (day: CalendarDay) => {
                this.DayCell(day)
              }, (day: CalendarDay, i: number) => `${i}-${day.day}-${day.state}`)
            }
            .width('100%')
          }
          .width('100%')
        }, (week: CalendarWeek, index: number) => `${index}-${week.title}`)
      }
      .width('100%')

      if (this.weeks.length === 0) {
        Text('服务器未返回本学期起止日期。')
          .fontSize(12)
          .fontColor($r('app.color.text_secondary'))
          .width('100%')
      }
    }
    .width('100%')
    .padding(16)
    .borderRadius(20)
    .backgroundColor($r('app.color.card_surface'))
    .border({ width: 1, color: $r('app.color.outline_variant') })
    .alignItems(HorizontalAlign.Start)
  }
}
