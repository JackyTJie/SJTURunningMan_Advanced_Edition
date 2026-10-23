import { useState } from 'react';

interface AboutPageProps {
  version: string;
  updateStatus: string;
  networkBusy: boolean;
  onCheckUpdate: () => void;
  onOpen: (kind: 'project' | 'shuiyuan') => void;
}

export function AboutPage({ version, updateStatus, networkBusy, onCheckUpdate, onOpen }: AboutPageProps) {
  const [section, setSection] = useState<'usage' | 'privacy'>('usage');
  return (
    <div className="about-page">
      <md-elevated-card className="surface-card about-hero">
        <div className="about-hero-body">
          <img src="/app-icon.png" alt="SJTU RunningMan 图标" className="about-icon" />
          <div className="about-copy">
            <h2>SJTU RunningMan</h2>
            <p className="about-version">
              <span className="mono">{version}</span>
              <span>·</span>
              <span>Tauri 2 · React 19 · Material Design 3</span>
            </p>
            <p className="about-desc">
              面向上海交通大学校园跑的研究与学习工具。离线生成并预览轨迹，登录后按计划上传。
            </p>
          </div>
          <span className="about-badge">DESKTOP</span>
        </div>
      </md-elevated-card>

      <div className="about-grid">
        <md-outlined-card className="surface-card">
          <div className="card-body">
            <div className="card-header">
              <div>
                <div className="card-eyebrow">维护</div>
                <h2 className="card-title">更新与社区</h2>
                <p className="card-sub">{updateStatus}</p>
              </div>
              <md-icon className="header-icon" aria-hidden="true">update</md-icon>
            </div>
            <div className="card-actions wrap">
              <md-filled-tonal-button onClick={onCheckUpdate} disabled={networkBusy}>
                <md-icon slot="icon" aria-hidden="true">refresh</md-icon>
                检查更新
              </md-filled-tonal-button>
              <md-outlined-button onClick={() => onOpen('project')}>
                <img slot="icon" className="community-icon github-icon" src="/github-mark.svg" alt="" aria-hidden="true" />
                GitHub
              </md-outlined-button>
              <md-outlined-button onClick={() => onOpen('shuiyuan')}>
                <img slot="icon" className="community-icon" src="/shuiyuan-mark.svg" alt="" aria-hidden="true" />
                水源社区
              </md-outlined-button>
            </div>
            <div className="about-meta">
              <div className="about-meta-item">
                <span>当前版本</span>
                <strong className="mono">{version}</strong>
              </div>
              <div className="about-meta-item">
                <span>更新渠道</span>
                <strong>GitHub Releases</strong>
              </div>
              <div className="about-meta-item">
                <span>界面</span>
                <strong>Material Design 3</strong>
              </div>
              <div className="about-meta-item">
                <span>运行时</span>
                <strong>Tauri 2 · React 19</strong>
              </div>
            </div>
            <div className="info-strip">
              <md-icon aria-hidden="true">info</md-icon>
              <div>
                <strong>从 Releases 获取新版本</strong>
                <span>检查更新只读取 GitHub Releases，不会自动下载或安装。</span>
              </div>
            </div>
          </div>
        </md-outlined-card>

        <md-outlined-card className="surface-card">
          <div className="card-body">
            <div className="card-header compact-header">
              <div>
                <div className="card-eyebrow">说明</div>
                <h2 className="card-title">{section === 'usage' ? '使用须知' : '数据与隐私'}</h2>
                <p className="card-sub">
                  {section === 'usage'
                    ? '本工具仅用于学习、研究和技术测试。'
                    : '凭据只存在于本次进程内。'}
                </p>
              </div>
              <md-outlined-segmented-button-set
                className="about-segments"
                aria-label="说明分类"
              >
                <md-outlined-segmented-button
                  label="使用"
                  selected={section === 'usage'}
                  onClick={() => setSection('usage')}
                />
                <md-outlined-segmented-button
                  label="隐私"
                  selected={section === 'privacy'}
                  onClick={() => setSection('privacy')}
                />
              </md-outlined-segmented-button-set>
            </div>
            {section === 'usage' ? (
              <ul className="about-list">
                <li>请遵守学校规定，不得将本软件用于伪造运动数据或规避体育锻炼要求。</li>
                <li>开始任务前先预览实际轨迹，确认距离、起终点与路线连续性。</li>
                <li>路线预览的内嵌地图使用 OpenStreetMap；规划器在系统浏览器中打开，默认百度、可切 OSM。在线底图需要网络。</li>
                <li>导入的路线存于用户数据目录，内置路线不可删除。</li>
              </ul>
            ) : (
              <ul className="about-list">
                <li>账号、密码、验证码与会话 Cookie 仅保存在进程内存中，退出账号或关闭程序即清除。</li>
                <li>日志只保留最近 250 行；本地仅保存外观、跑步参数与导入路线。</li>
                <li>学期统计与打卡记录只用于界面展示，不写入磁盘。</li>
                <li>验证码识别请求只发送图片，不附带账号、密码或登录 Cookie。</li>
              </ul>
            )}
          </div>
        </md-outlined-card>
      </div>

      <div className="about-foot">
        <span>SJTU RunningMan · 仅用于学习与研究</span>
        <span className="mono">{version}</span>
      </div>
    </div>
  );
}
