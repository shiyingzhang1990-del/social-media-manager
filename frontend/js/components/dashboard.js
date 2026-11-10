/**
 * Dashboard view - overview stats and platform summaries.
 */
const DashboardView = (() => {
  function platformIcon(key) {
    const icons = { weibo: 'Wb', wechat: 'Wx', douyin: 'Dy', xiaohongshu: 'Xhs', bilibili: 'Bz' };
    return icons[key] || key[0].toUpperCase();
  }

  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const [stats, platformSummary, recentActivity, nextSchedules, calendarData] = await Promise.all([
        API.getStats(),
        API.getPlatformSummary(),
        API.getRecentActivity(10),
        API.getNextSchedules(5),
        API.getCalendarSchedules(),
      ]);

      main.innerHTML = `
        <div class="page-header"><h2>总览仪表盘</h2></div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">总账号数</div>
            <div class="stat-value" style="color:var(--primary)">${stats.total_accounts}</div>
            <div class="stat-sub">活跃 ${stats.active_accounts} · 异常 ${stats.error_accounts}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">内容总数</div>
            <div class="stat-value" style="color:var(--success)">${stats.total_content}</div>
            <div class="stat-sub">已发布 ${stats.published_content} · 草稿 ${stats.draft_content}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">待发定时</div>
            <div class="stat-value" style="color:var(--warning)">${stats.pending_schedules}</div>
            <div class="stat-sub">今日已发 ${stats.today_published}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">今日发布</div>
            <div class="stat-value" style="color:${stats.today_failed > 0 ? 'var(--danger)' : 'var(--success)'}">${stats.today_published}</div>
            <div class="stat-sub">失败 ${stats.today_failed}</div>
          </div>
        </div>

        <div style="margin-bottom:24px">
          <h3 style="font-size:15px;margin-bottom:12px;font-weight:600">各平台概览</h3>
          <div class="platform-summary">
            ${Object.entries(platformSummary.platforms).map(([key, p]) => `
              <div class="platform-card">
                <div class="plat-name">
                  <span class="platform-badge plat-${key}">${platformIcon(key)}</span>
                  ${p.name}
                </div>
                <div class="plat-stat">账号: <strong>${p.total_accounts}</strong> (活跃 ${p.active_accounts})</div>
                <div class="plat-stat">已发布: <strong>${p.total_published}</strong></div>
                <div class="plat-stat">今日: <strong>${p.today_published}</strong></div>
              </div>
            `).join('')}
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px">
          <div class="card">
            <div class="card-header">最近动态</div>
            <div class="card-body" style="padding:8px 20px">
              ${recentActivity.activities.length === 0
                ? '<div class="empty-state" style="padding:20px">暂无动态</div>'
                : `<ul class="activity-list">
                  ${recentActivity.activities.map(a => `
                    <li class="activity-item">
                      <span class="activity-dot ${a.status}"></span>
                      <div>
                        <strong>${a.platform}</strong> ·
                        ${a.action === 'publish' ? '发布' : a.action}
                        ${a.status === 'success' ? '成功' : '失败'}
                        ${a.error_message ? `<span style="color:var(--danger)">: ${a.error_message}</span>` : ''}
                        <div style="font-size:11px;color:var(--text-secondary);margin-top:2px">
                          ${new Date(a.created_at).toLocaleString('zh-CN')}
                          · ${a.duration_ms}ms
                        </div>
                      </div>
                    </li>
                  `).join('')}
                </ul>`
              }
            </div>
          </div>
          <div class="card">
            <div class="card-header">即将发布的定时</div>
            <div class="card-body" style="padding:8px 20px">
              ${nextSchedules.schedules.length === 0
                ? '<div class="empty-state" style="padding:20px">暂无定时任务</div>'
                : `<ul class="activity-list">
                  ${nextSchedules.schedules.map(s => `
                    <li class="activity-item">
                      <span class="activity-dot" style="background:var(--warning)"></span>
                      <div>
                        <strong>${s.platform}</strong>
                        <div style="font-size:11px;color:var(--text-secondary)">
                          计划于 ${new Date(s.scheduled_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    </li>
                  `).join('')}
                </ul>`
              }
            </div>
          </div>
        </div>

        <!-- Mini Calendar -->
        <div class="card" style="margin-bottom:24px">
          <div class="card-header">内容日历</div>
          <div class="card-body">${renderMiniCalendar(calendarData)}</div>
        </div>
      `;
    } catch (e) {
      main.innerHTML = `<div class="empty-state">加载失败: ${e.message}</div>`;
    }
  }

  function renderMiniCalendar(data) {
    var year = data.year || new Date().getFullYear();
    var month = data.month || (new Date().getMonth() + 1);
    var schedules = data.schedules || [];

    var postsByDay = {};
    schedules.forEach(function(s) {
      var d = new Date(s.scheduled_at);
      if (d.getFullYear() === year && d.getMonth() + 1 === month) {
        var day = d.getDate();
        postsByDay[day] = (postsByDay[day] || 0) + 1;
      }
    });

    var firstDay = new Date(year, month - 1, 1);
    var lastDay = new Date(year, month, 0);
    var startDow = firstDay.getDay();
    var daysInMonth = lastDay.getDate();
    var today = new Date();
    var dowNames = ['日', '一', '二', '三', '四', '五', '六'];
    var platColors = { xiaohongshu: '#ff2442', weibo: '#e6162d', bilibili: '#00a1d6', douyin: '#111', wechat: '#07c160' };

    var html = '<div class="mini-calendar">';
    dowNames.forEach(function(n) { html += '<div class="mini-cal-cell mini-cal-header">' + n + '</div>'; });
    for (var i = 0; i < startDow; i++) { html += '<div class="mini-cal-cell mini-cal-empty"></div>'; }
    for (var d = 1; d <= daysInMonth; d++) {
      var cls = 'mini-cal-cell';
      if (today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === d) cls += ' mini-cal-today';
      var count = postsByDay[d] || 0;
      html += '<div class="' + cls + '"><span class="mini-cal-day">' + d + '</span>' + (count > 0 ? '<span class="mini-cal-dot"></span>' : '') + '</div>';
    }
    html += '</div>';
    return html;
  }

  return { render };
})();
