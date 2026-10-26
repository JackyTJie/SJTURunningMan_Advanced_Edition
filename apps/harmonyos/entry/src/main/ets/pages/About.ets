import { promptAction } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { AppConfig } from '../config/AppConfig';
import { UpdateChecker, UpdateResult, UpdateResultKind, ReleaseInfo } from '../service/UpdateChecker';

/**
 * 关于页（二级页，挂载于 Index 的 Navigation 导航栈）
 * 迁移自 Android: com.sjtu.runner.ui.components.AboutDialog
 * - Android 的 TopAppBar action 弹窗 -> NavDestination 二级页（系统标题栏 + 返回键）
 * - 内容一致：版本徽标 / 免责声明 / 署名 / 检查更新 / 仓库、水源、下载链接
 */
@Component
export struct AboutPage {
  /** 是否正在检查更新 */
  @State checking: boolean = false;
  /** 检查更新结果 */
  @State result: UpdateResult | undefined = undefined;

  /** 检查更新（等价 AboutDialog 的 "检查更新" 按钮） */
  private async checkUpdate(): Promise<void> {
    if (this.checking) {
      return;
    }
    this.checking = true;
    try {
      this.result = await UpdateChecker.checkForUpdates(AppConfig.VERSION_NAME);
    } finally {
      this.checking = false;
    }
  }

  /** 用系统能力打开外部链接（等价 Android Intent.ACTION_VIEW） */
  private openUrl(url: string): void {
    if (url.length === 0) {
      return;
    }
    const context = getContext(this) as common.UIAbilityContext;
    try {
      context.openLink(url).catch((err: Error) => {
        promptAction.showToast({ message: `无法打开链接: ${err.message}`, duration: 2000 });
      });
    } catch (e) {
      promptAction.showToast({ message: `无法打开链接: ${(e as Error).message}`, duration: 2000 });
    }
  }

  /** 检查更新结果文案 */
  private resultText(): string {
    const result = this.result;
    if (result === undefined) {
      return '';
    }
    if (result.kind === UpdateResultKind.UP_TO_DATE) {
      return `已是最新版本 ${result.latestTag}`;
    }
    if (result.kind === UpdateResultKind.UPDATE_AVAILABLE) {
      return `发现新版本 ${result.latestTag}`;
    }
    return `检查更新失败：${result.reason}`;
  }

  private resultColor(): Resource {
    const result = this.result;
    if (result !== undefined && result.kind === UpdateResultKind.UPDATE_AVAILABLE) {
      return $r('app.color.success_color');
    }
    if (result !== undefined && result.kind === UpdateResultKind.FAILED) {
      return $r('app.color.error_color');
    }
    // 已是最新版本（等价 Android LocalAppColors.current.success）
    return $r('app.color.success_color');
  }

  private hasUpdate(): boolean {
    const result = this.result;
    return result !== undefined && result.kind === UpdateResultKind.UPDATE_AVAILABLE && result.latest !== null;
  }

  @Builder
  LinkButton(label: string, url: string) {
    Button() {
      Row({ space: 6 }) {
        Text(label)
          .fontSize(14)
          .fontColor($r('app.color.brand_primary'))
      }
    }
    .height(40)
    .borderRadius(20)
    .backgroundColor(Color.Transparent)
    .border({ width: 1, color: $r('app.color.outline_variant') })
    .padding({ left: 14, right: 14 })
    .onClick(() => {
      this.openUrl(url);
    })
  }

  build() {
    NavDestination() {
      Scroll() {
        Column({ space: 16 }) {
          // ===== 头部：Logo + 名称 + 版本徽标 =====
          Column({ space: 12 }) {
            Column() {
              Image($r('app.media.app_icon'))
                .width(96)
                .height(96)
                .borderRadius(16)
                .objectFit(ImageFit.Cover)
            }
            .width(96)
            .height(96)
            .borderRadius(16)

            Row({ space: 8 }) {
              Text('交我润')
                .fontSize(22)
                .fontWeight(FontWeight.Bold)
                .fontColor($r('app.color.text_primary'))
              Text(`v${AppConfig.VERSION_NAME}`)
                .fontSize(12)
                .fontWeight(FontWeight.Medium)
                .fontColor($r('app.color.brand_on_primary_container'))
                .backgroundColor($r('app.color.brand_primary_container'))
                .padding({ left: 10, right: 10, top: 4, bottom: 4 })
                .borderRadius(8)
            }
            .alignItems(VerticalAlign.Center)
          }
          .width('100%')
          .alignItems(HorizontalAlign.Center)

          // ===== 免责声明 =====
          Column({ space: 8 }) {
            Text(AppConfig.DISCLAIMER_TEXT)
              .fontSize(12)
              .lineHeight(18)
              .fontColor($r('app.color.text_secondary'))
              .width('100%')
          }
          .width('100%')
          .padding(16)
          .borderRadius(16)
          .backgroundColor($r('app.color.card_surface'))
          .border({ width: 1, color: $r('app.color.outline_variant') })
          .alignItems(HorizontalAlign.Start)

          // ===== 署名 =====
          Column({ space: 8 }) {
            Text('项目信息')
              .fontSize(14)
              .fontWeight(FontWeight.Medium)
              .fontColor($r('app.color.text_primary'))
            Text(AppConfig.CREDITS)
              .fontSize(12)
              .lineHeight(20)
              .fontColor($r('app.color.text_secondary'))
              .width('100%')
            Text(AppConfig.HARMONYOS_CREDITS)
              .fontSize(12)
              .lineHeight(20)
              .fontColor($r('app.color.text_secondary'))
              .width('100%')
          }
          .width('100%')
          .padding(16)
          .borderRadius(16)
          .backgroundColor($r('app.color.card_surface'))
          .border({ width: 1, color: $r('app.color.outline_variant') })
          .alignItems(HorizontalAlign.Start)

          // ===== 检查更新 =====
          Column({ space: 12 }) {
            Row({ space: 10 }) {
              Text('版本更新')
                .fontSize(14)
                .fontWeight(FontWeight.Medium)
                .fontColor($r('app.color.text_primary'))
                .layoutWeight(1)
              Button() {
                Row({ space: 6 }) {
                  if (this.checking) {
                    LoadingProgress()
                      .width(16)
                      .height(16)
                      .color($r('app.color.brand_primary'))
                  }
                  Text(this.checking ? '检查中…' : '检查更新')
                    .fontSize(14)
                    .fontColor($r('app.color.brand_primary'))
                }
              }
              .height(36)
              .borderRadius(18)
              .backgroundColor(Color.Transparent)
              .border({ width: 1, color: $r('app.color.brand_primary') })
              .padding({ left: 14, right: 14 })
              .enabled(!this.checking)
              .onClick(() => {
                this.checkUpdate();
              })
            }
            .width('100%')
            .alignItems(VerticalAlign.Center)

            if (this.result !== undefined) {
              Text(this.resultText())
                .fontSize(12)
                .fontColor(this.resultColor())
                .width('100%')
            }
          }
          .width('100%')
          .padding(16)
          .borderRadius(16)
          .backgroundColor($r('app.color.card_surface'))
          .border({ width: 1, color: $r('app.color.outline_variant') })
          .alignItems(HorizontalAlign.Start)

          // ===== 链接 =====
          Row({ space: 10 }) {
            this.LinkButton('仓库', AppConfig.GITHUB_REPO_URL)
            this.LinkButton('水源', AppConfig.SHUIYUAN_TOPIC_URL)
            if (this.hasUpdate()) {
              this.LinkButton('下载', this.downloadUrl())
            }
          }
          .width('100%')
          .justifyContent(FlexAlign.Center)

          Text('本项目仅供学习、研究和技术测试，请勿用于伪造运动数据或规避体育锻炼要求。')
            .fontSize(12)
            .lineHeight(18)
            .fontColor($r('app.color.text_secondary'))
            .textAlign(TextAlign.Center)
            .width('100%')
            .padding({ left: 8, right: 8 })
        }
        .width('100%')
        // NavDestination 自带标题栏在布局中占位（不是悬浮层），内容只需常规内边距。
        .padding({ left: 16, right: 16, top: 16, bottom: 32 })
      }
      .scrollable(ScrollDirection.Vertical)
      .scrollBar(BarState.Auto)
      .width('100%')
      .height('100%')
      .align(Alignment.Top)
    }
    .title('关于')
    .backgroundColor($r('app.color.page_background'))
  }

  /** 最新版本的下载地址（缺省回落仓库 releases 页） */
  private downloadUrl(): string {
    const result = this.result;
    if (result === undefined || result.latest === null) {
      return `${AppConfig.GITHUB_REPO_URL}/releases`;
    }
    const latest: ReleaseInfo = result.latest;
    return latest.url.length > 0 ? latest.url : `${AppConfig.GITHUB_REPO_URL}/releases`;
  }
}
