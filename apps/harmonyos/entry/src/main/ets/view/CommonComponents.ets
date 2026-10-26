/**
 * 公共 UI 小组件
 * 迁移自 Android MainScreen.kt 中的 DropdownSelection @Composable
 * （SelectOption 为 ArkUI 组件全局类型，无需导入）
 *
 * HarmonyOS 系统应用风格适配：图标统一使用 HarmonyOS Symbol 系统符号
 * （SymbolGlyph / $r('sys.symbol.*')），不再使用 emoji 占位。
 * 任务设置的每一行都用本文件的自绘 SettingCard：HdsListItemCard 的自定义
 * 后缀构建器不参与尺寸测量，控件会溢出卡片（详见 HDS_CARD_RADIUS 处的说明）。
 */
import { promptAction } from '@kit.ArkUI';

/**
 * 一级页顶部标题栏高度（vp）。
 *
 * 由 Index.ets 自绘（标题与右上角“账号/关于”图标按钮同一行），作为 Navigation 内容区的
 * 第一个子节点参与正常布局流，与二级页 NavDestination 自带标题栏的高度保持一致，
 * 进出二级页时顶部栏的跳动最小。
 * 注意：它是布局中的实体高度，滚动内容不需要再为它预留 top padding（HDS 时代才需要）。
 */
export const APP_HEADER_HEIGHT: number = 56;

/**
 * 任务设置卡片（自绘，视觉对齐 HdsListItemCard）的几何常量，单位 vp。
 *
 * 为什么自绘：HdsListItemCard 的 suffixItem 只接受 Builder（SuffixCustomBuilder），
 * 该自定义构建器的内容不参与卡片的尺寸测量 —— 实测把一行选项控件（原胶囊组，
 * 现将常用的任务设置项改为系统下拉框 Select）放进后缀区时，
 * 卡片高度仍是 64vp（按 SuffixText 的固定行高），内部控件却按屏宽排版并溢出卡片
 * （控件画到了卡片外、与上一张卡片的按钮重叠）。给后缀内容显式设宽度只解决了横向溢出，
 * 纵向仍需给卡片写死高度。这里改用原生 Column 自绘卡片：内容由 ArkUI 正常测量，
 * 尺寸自适应，不再需要估算高度。
 */
export const HDS_CARD_RADIUS: number = 16;
export const HDS_CARD_PADDING: number = 16;
/**
 * 状态圆点（必填/已完成标记）字号，单位 vp
 */
export const HDS_STATUS_DOT_SIZE: number = 18;
/**
 * 状态圆点颜色（品牌主色，表示「已完成/已确认」，非报错）。
 * 不用 $r('app.color.*')：SymbolGlyph 的 fontColor 只接受 Array<ResourceColor>，
 * 直接给 Resource 资源引用时字体颜色不生效（实测仍为默认色），故用字面量。
 */
export const HDS_STATUS_DOT_COLOR: string = '#6650A4';
/**
 * SettingCard 图标字号，与 HdsListItemCard 的 22vp 对齐（44→48px 的实测差可直接忽略）。
 */
const SETTING_ICON_SIZE: number = 20;
/**
 * 图标列宽度（vp）：图标居中于 HdsListItemCard 前缀图标所占的 [56,140]px 区间内。
 * 与 SETTING_LABEL_WIDTH 之和决定标签起点：56 + 2.24×(35+65) = 280px，
 * 即安卓/iOS/HDS 原生列表行的标签左边缘（实测 HdsListItemCard 的标签起点正是 280）。
 */
const SETTING_ICON_COLUMN: number = 35;
/**
 * 标签列宽度（vp）。
 * 下界由两条约束共同决定：
 * 1) 与 SETTING_ICON_COLUMN 一起把标签起点钉在 x=280px，各行（含静态信息行）左边缘一致；
 * 2) ArkUI 的 Text 有 64vp 最小宽度，低于此值「跑步次数」这类 4 字标签会折行
 *    （实测 43vp 时四行有三行折成两行）。故取 65vp，既满足最小宽度又钉住起点。
 */
const SETTING_LABEL_WIDTH: number = 65;
/**
 * 并排布局下「图标列 + 标签列」的总宽度（vp）。
 * 控件列里需要与标签左对齐的内容（如目标距离的数值行）用这个值做左缩进，
 * 不要再自己拼 35 + 65，否则两处常量一改就会错位。
 */
export const SETTING_CONTENT_INDENT: number = SETTING_ICON_COLUMN + SETTING_LABEL_WIDTH;

/**
 * 构造 Select 选项数组
 */
export function toSelectOptions(values: string[]): SelectOption[] {
  const options: SelectOption[] = [];
  for (let i = 0; i < values.length; i++) {
    const option: SelectOption = { value: values[i] };
    options.push(option);
  }
  return options;
}

/**
 * 带交互控件的参数行卡片（视觉对齐 HdsListItemCard，尺寸由 ArkUI 正常测量）。
 *
 * 用途与理由见文件头与 HDS_CARD_RADIUS 的说明：HdsListItemCard 的自定义后缀
 * 不参与测量，控件会溢出卡片；本组件用原生 Row/Column 复刻其外观，
 * 左侧系统符号 + 标签文本，右侧 @BuilderParam 承载任意控件（胶囊组/时间输入/滑杆）。
 *
 * fullWidth：控件横向占满整张卡片（标签移到控件上方）。
 * 原因：ArkUI 的 Text 有 64vp 的最小宽度且不随内容收缩，并排布局下即便卡片很宽，
 * 标签列也会吃掉一截（实测控件列只剩约 283vp）。
 * 需要宽控件的行（目标距离滑杆）用 fullWidth，控件拿满约 500vp；
 * 窄控件行（跑步次数下拉框、开始时间）仍用并排布局。
 *
 * 并排布局下图标列固定为 SETTING_ICON_COLUMN、标签列固定为 SETTING_LABEL_WIDTH，
 * 因此任务设置各行（含静态信息行）的标签左边缘严格一致、控件列起点也一致；
 * 前缀槽位用 prefixSymbol 承载「必填/已完成」状态标记，无标记时留空占位而不塌缩。
 */
@Component
export struct SettingCard {
  /** 标签文本 */
  label: string = '';
  /** 左侧系统符号（不传则不渲染图标列） */
  symbol: Resource | undefined = undefined;
  /** 控件是否横向占满卡片（标签移到上方） */
  fullWidth: boolean = false;
  /**
   * 纯静态信息行的右侧文本（如「2026-10-13」）。
   * 传值时不接收 control builder，把该值右对齐渲染在控件列。
   */
  valueText: string = '';
  /**
   * 标签右侧的说明文本，以「圈 i」图标呈现，点按弹出对话框展示全文。
   * 用途：把占版面的长说明（如随机波动规则）折叠起来，需要时再点开看。
   */
  infoText: string = '';
  /**
   * 自定义前缀（不传则渲染 symbol），只在非 fullWidth 布局下生效：
   * 传值时以该符号 + HDS_STATUS_DOT_COLOR 呈现，用作「必填/已完成」等状态标记。
   */
  prefixSymbol: Resource | undefined = undefined;
  /**
   * 标签行读数（如「目标距离 4.0 km」中的 `4.0 km`）。
   *
   * 走 AppStorage 而不是父组件传值：ArkUI 会把 `@BuilderParam` 的箭头函数 bind 成子组件的
   * `this`，闭包里读父组件 @State 会读到陈旧值（实测滑杆已到 1.6、父组件渲染的读数仍是 4.0），
   * 而 `@StorageProp` 不依赖 `this`。写入方（滑杆 onChange）用同一个键。
   */
  @StorageProp('distanceKmText') labelTrailingValue: string = '';
  /** 卡片主体内容 */
  @BuilderParam control: () => void;

  build() {
    if (this.fullWidth) {
      Column() {
        Row() {
          Row() {
            if (this.symbol !== undefined) {
              SymbolGlyph(this.symbol)
                .fontSize(SETTING_ICON_SIZE)
                .fontColor([$r('app.color.brand_primary')])
            }
          }
          .width(SETTING_ICON_COLUMN)
          .justifyContent(FlexAlign.Center)

          Text(this.label)
            .fontSize(16)
            .fontColor($r('app.color.text_primary'))
            .maxLines(1)

          // 标签行读数（如「目标距离 4.0 km」）：值来自 AppStorage，拖动滑杆时能实时刷新
          if (this.labelTrailingValue.length > 0) {
            Text(this.labelTrailingValue)
              .fontSize(19)
              .fontWeight(FontWeight.Bold)
              .fontColor($r('app.color.brand_primary'))
              .maxLines(1)
              .margin({ left: 8 })
          }

          if (this.infoText.length > 0) {
            SymbolGlyph($r('sys.symbol.info_circle'))
              .fontSize(16)
              .fontColor([$r('app.color.text_secondary')])
              .margin({ left: 6 })
              .onClick(() => {
                promptAction.showDialog({ message: this.infoText });
              })
          }
        }
        .width('100%')
        .alignItems(VerticalAlign.Center)

        Column() {
          this.control()
        }
        .width('100%')
        .alignItems(HorizontalAlign.Start)
        // 控件列紧贴标签行，视觉上像标签的续行
        .margin({ top: 4 })
      }
      .width('100%')
      .padding(HDS_CARD_PADDING)
      .borderRadius(HDS_CARD_RADIUS)
      .backgroundColor($r('app.color.card_surface'))
    } else {
      Row() {
        // 图标列固定宽度且图标居中：无 symbol 时留空占位，保证各行标签左边缘对齐。
        Row() {
          if (this.prefixSymbol !== undefined) {
            SymbolGlyph(this.prefixSymbol)
              .fontSize(HDS_STATUS_DOT_SIZE)
              .fontColor([HDS_STATUS_DOT_COLOR])
          } else if (this.symbol !== undefined) {
            SymbolGlyph(this.symbol)
              .fontSize(SETTING_ICON_SIZE)
              .fontColor([$r('app.color.brand_primary')])
          }
        }
        .width(SETTING_ICON_COLUMN)
        .height(SETTING_ICON_COLUMN)
        .justifyContent(FlexAlign.Center)
        .alignItems(VerticalAlign.Center)

        Text(this.label)
          .fontSize(16)
          .fontColor($r('app.color.text_primary'))
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .constraintSize({ minWidth: SETTING_LABEL_WIDTH })

        if (this.infoText.length > 0) {
          // 说明折叠成「圈 i」：点按弹出全文，避免长说明把卡片撑高
          SymbolGlyph($r('sys.symbol.info_circle'))
            .fontSize(16)
            .fontColor([$r('app.color.text_secondary')])
            .margin({ left: 6 })
            .onClick(() => {
              promptAction.showDialog({ message: this.infoText });
            })
        }

        if (this.valueText.length > 0) {
          // 静态信息行：值右对齐，与交互行的控件列起点一致
          Text(this.valueText)
            .fontSize(15)
            .fontColor($r('app.color.text_primary'))
            .layoutWeight(1)
            .textAlign(TextAlign.End)
        } else {
          // 控件右对齐：Row 内先占位再放控件，控件即贴卡片右内边距
          Row() {
            Blank()
            this.control()
          }
          .layoutWeight(1)
          .justifyContent(FlexAlign.End)
          .alignItems(VerticalAlign.Center)
        }
      }
      .width('100%')
      .padding(HDS_CARD_PADDING)
      .borderRadius(HDS_CARD_RADIUS)
      .backgroundColor($r('app.color.card_surface'))
      .alignItems(VerticalAlign.Center)
    }
  }
}

/**
 * 下拉选择（等价 Android DropdownSelection）
 */
@Component
export struct DropdownSelection {
  options: string[] = [];
  selected: string = '';
  selectedIdx: number = 0;
  onSelect: (value: string) => void = (value: string) => {
  };

  build() {
    Select(toSelectOptions(this.options))
      .selected(this.selectedIdx)
      .value(this.selected)
      .fontColor($r('app.color.text_primary'))
      .font({ size: 14 })
      .optionFont({ size: 14 })
      .selectedOptionFont({ size: 14 })
      .onSelect((index: number, text?: string) => {
        if (text !== undefined) {
          this.onSelect(text);
        }
      })
  }
}
