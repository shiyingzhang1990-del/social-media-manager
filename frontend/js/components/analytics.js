/**
 * Analytics view - overview, platform comparison, trends, publishing stats.
 */
const AnalyticsView = (() => {
  const PLATFORM_NAMES = { xiaohongshu: '小红书', weibo: '微博', bilibili: 'B站', douyin: '抖音', wechat: '微信' };
  const PLATFORM_COLORS = { xiaohongshu: '#ff2442', weibo: '#e6162d', bilibili: '#00a1d6', douyin: '#111', wechat: '#07c160' };

  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const [overview, trends, pubStats] = await Promise.all([
        API.getAnalyticsOverview(30),
        API.getTrends(14),
        API.getPublishingStats(),
      ]);

      let html = '<div class="page-header"><h2>数据分析</h2></div>';

      // ── KPI Cards ───────────────────────────────────────────
      html += '<div class="stats-grid">';
      html += kpiCard('总账号', overview.accounts.total, (overview.accounts.active + ' 活跃'), 'var(--primary)');
      html += kpiCard('账号健康', overview.accounts.healthy, (overview.accounts.warning + ' 警告 · ' + overview.accounts.unhealthy + ' 异常'), 'var(--success)');
      html += kpiCard('发布成功率', overview.publishing.success_rate + '%', (overview.publishing.success_count + ' / ' + overview.publishing.total_attempts + ' 次'), 'var(--success)');
      html += kpiCard('待处理', overview.publishing.pending_schedules, ('失败: ' + overview.publishing.failed_schedules), 'var(--warning)');
      html += kpiCard('内容总量', overview.content.total + '', (overview.content.published + ' 已发布 · ' + overview.content.failed + ' 失败'), 'var(--primary)');
      html += kpiCard('平均耗时', overview.publishing.avg_duration_ms + 'ms', '发布响应时间', 'var(--text-secondary)');
      html += '</div>';

      // ── Platform Distribution ───────────────────────────────
      html += '<div class="card" style="margin-bottom:20px"><div class="card-header">平台分布</div><div class="card-body">';
      const platDist = overview.platform_distribution || {};
      const maxPlat = Math.max(1, ...Object.values(platDist));
      for (const plat in platDist) {
        const pct = Math.round(platDist[plat] / maxPlat * 100);
        html += '<div class="analytics-bar-row"><div class="analytics-bar-label">' +
          '<span class="platform-badge plat-' + plat + '">' + (PLATFORM_NAMES[plat] || plat) + '</span>' +
          '</div><div class="analytics-bar-track"><div class="analytics-bar-fill" style="width:' + pct + '%;background:' + (PLATFORM_COLORS[plat] || '#3699ff') + '"></div></div>' +
          '<span class="analytics-bar-value">' + platDist[plat] + '</span></div>';
      }
      html += '</div></div>';

      // ── Daily Trend Bar Chart ───────────────────────────────
      html += '<div class="card" style="margin-bottom:20px"><div class="card-header">每日发布趋势 (近7日)</div><div class="card-body">';
      const daily = overview.daily_publishes || [];
      const maxDaily = Math.max(1, ...daily.map(function(d) { return d.count; }));
      html += '<div class="trend-chart">';
      daily.forEach(function(d) {
        const h = Math.round(d.count / maxDaily * 100);
        html += '<div class="trend-bar-col"><div class="trend-bar" style="height:' + Math.max(h, 2) + 'px"></div><div class="trend-bar-label">' + d.date + '</div><div class="trend-bar-value">' + d.count + '</div></div>';
      });
      html += '</div></div></div>';

      // ── Publishing Stats by Platform ───────────────────────
      html += '<div class="card" style="margin-bottom:20px"><div class="card-header">各平台发布统计</div><div class="card-body">';
      html += '<div class="table-wrapper"><table><thead><tr><th>平台</th><th>总发布</th><th>成功</th><th>成功率</th><th>平均耗时</th></tr></thead><tbody>';
      for (const plat in pubStats.platform_stats) {
        const ps = pubStats.platform_stats[plat];
        html += '<tr><td><span class="platform-badge plat-' + plat + '">' + (PLATFORM_NAMES[plat] || plat) + '</span></td>' +
          '<td>' + ps.total + '</td><td>' + ps.success + '</td>' +
          '<td><span class="badge ' + (ps.success_rate >= 80 ? 'badge-success' : ps.success_rate >= 50 ? 'badge-warning' : 'badge-danger') + '">' + ps.success_rate + '%</span></td>' +
          '<td>' + ps.avg_duration_ms + 'ms</td></tr>';
      }
      html += '</tbody></table></div></div></div>';

      // ── Best Publishing Hours ──────────────────────────────
      html += '<div class="card" style="margin-bottom:20px"><div class="card-header">最佳发布时段 (按成功率)</div><div class="card-body">';
      const bestHours = pubStats.best_hours || [];
      bestHours.forEach(function(h) {
        html += '<div class="analytics-bar-row"><div class="analytics-bar-label">' + String(h.hour).padStart(2, '0') + ':00</div>' +
          '<div class="analytics-bar-track"><div class="analytics-bar-fill" style="width:' + Math.min(h.rate, 100) + '%;background:var(--success)"></div></div>' +
          '<span class="analytics-bar-value">' + h.success + '/' + h.total + ' (' + h.rate + '%)</span></div>';
      });
      html += '</div></div>';

      // ── Platform Trends ─────────────────────────────────────
      html += '<div class="card"><div class="card-header">各平台14日趋势</div><div class="card-body">';
      const platTrends = trends.platform_trends || {};
      for (const plat in platTrends) {
        const td = platTrends[plat];
        const maxTd = Math.max(1, ...td.map(function(d) { return d.success + d.failed; }));
        html += '<div style="margin-bottom:14px"><div style="font-size:13px;font-weight:600;margin-bottom:6px"><span class="platform-badge plat-' + plat + '">' + (PLATFORM_NAMES[plat] || plat) + '</span></div>';
        html += '<div class="trend-chart" style="height:40px">';
        td.forEach(function(d) {
          const h = Math.round((d.success + d.failed) / maxTd * 100);
          html += '<div class="trend-bar-col" style="width:' + (100 / td.length) + '%"><div class="trend-bar" style="height:' + Math.max(h, 3) + 'px;background:' + (PLATFORM_COLORS[plat] || '#3699ff') + '"></div></div>';
        });
        html += '</div></div>';
      }
      html += '</div></div>';

      main.innerHTML = html;
    } catch (e) {
      main.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
    }
  }

  function kpiCard(label, value, sub, color) {
    return '<div class="stat-card"><div class="stat-label">' + label + '</div>' +
      '<div class="stat-value" style="color:' + color + '">' + value + '</div>' +
      '<div class="stat-sub">' + sub + '</div></div>';
  }

  return { render: render };
})();
