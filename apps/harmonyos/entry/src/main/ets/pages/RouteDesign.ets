import { promptAction } from '@kit.ArkUI';
import { webview } from '@kit.ArkWeb';
import { GpsPoint } from '../model/RouteInfo';
import { RouteManager } from '../service/RouteManager';
import { MainViewModel } from '../viewmodel/MainViewModel';
import { LogLevel } from '../viewmodel/TaskModels';

/**
 * 路线设计页（二级页，挂载于 Index 的 Navigation 导航栈）
 * 迁移自 Android: com.sjtu.runner.route.RouteDesignActivity
 * - WebView(assets/route_design.html) -> Web($rawfile('route_design.html'))
 * - addJavascriptInterface(AndroidBridge, "AndroidInterface") -> javaScriptProxy(同名桥)
 *   HTML 内调用 window.AndroidInterface.onSaveRoute(name, pointsJson) 的逻辑无需改动。
 * - setResult(RESULT_OK) + finish() -> 通知 ViewModel 刷新路线列表 + navStack.pop()
 * - 自绘顶栏/返回键 -> NavDestination 原生标题栏与系统返回控件
 */
class RouteBridge {
  private owner: RouteDesignPage | null = null;

  bindOwner(owner: RouteDesignPage): void {
    this.owner = owner;
  }

  /** HTML 桥接入口（等价 @JavascriptInterface onSaveRoute） */
  onSaveRoute(routeName: string, pointsJson: string): void {
    if (this.owner !== null) {
      this.owner.handleSaveRoute(routeName, pointsJson);
    }
  }
}

@Component
export struct RouteDesignPage {
  controller: webview.WebviewController = new webview.WebviewController();
  private bridge: RouteBridge = new RouteBridge();
  private viewModel: MainViewModel = MainViewModel.getInstance();
  navStack: NavPathStack = new NavPathStack();
  private isSaving: boolean = false;

  aboutToAppear(): void {
    this.bridge.bindOwner(this);
  }

  /** 解析 HTML 传来的坐标 JSON：[{lng, lat}, ...] */
  private parsePointsJson(json: string): GpsPoint[] {
    const result: GpsPoint[] = [];
    try {
      const parsed = JSON.parse(json) as Array<Record<string, Object>>;
      for (let i = 0; i < parsed.length; i++) {
        const lng = parsed[i]['lng'];
        const lat = parsed[i]['lat'];
        if (typeof lng === 'number' && typeof lat === 'number') {
          result.push(new GpsPoint(lng as number, lat as number));
        }
      }
    } catch (e) {
      // JSON 无效时返回空列表
    }
    return result;
  }

  /** 保存路线（等价 AndroidBridge.onSaveRoute 内部逻辑） */
  handleSaveRoute(routeName: string, pointsJson: string): void {
    if (this.isSaving) {
      return;
    }
    this.isSaving = true;
    try {
      const points = this.parsePointsJson(pointsJson);
      if (points.length === 0) {
        promptAction.showToast({ message: '坐标点无效', duration: 1500 });
        return;
      }

      const route = RouteManager.getInstance().saveCustomRoute(routeName, points);
      if (route !== null) {
        promptAction.showToast({
          message: `路线「${route.name}」保存成功！共${points.length}个点`,
          duration: 2500
        });
        // 等价 setResult(RESULT_OK, intent.putExtra(EXTRA_ROUTE_SAVED, true)) + finish()
        this.viewModel.logMsg(LogLevel.SUCCESS, '新路线已创建，刷新列表');
        this.viewModel.refreshRoutes();
        this.navStack.pop();
      } else {
        promptAction.showToast({ message: '保存失败', duration: 1500 });
      }
    } catch (e) {
      promptAction.showToast({ message: `保存出错: ${(e as Error).message}`, duration: 1500 });
    } finally {
      this.isSaving = false;
    }
  }

  build() {
    NavDestination() {
      Web({ src: $rawfile('route_design.html'), controller: this.controller })
        .javaScriptAccess(true)
        .domStorageAccess(true)
        .zoomAccess(true)
        .width('100%')
        .height('100%')
        .javaScriptProxy({
          object: this.bridge,
          name: 'AndroidInterface',
          methodList: ['onSaveRoute'],
          controller: this.controller
        })
    }
    .title('设计路线')
  }
}
