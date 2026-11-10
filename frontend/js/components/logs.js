/**
 * Publish logs view.
 */
const LogsView = (() => {
  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const activity = await API.getRecentActivity(100);
      const logs = activity.activities;

      let html = `
        <div class="page-header">
          <h2>发布日志</h2>
          <span style="color:var(--text-secondary);font-size:13px">最近 ${logs.length} 条记录</span>
        </div>
      `;

      if (logs.length === 0) {
        html += `<div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <p>暂无发布日志</p>
        </div>`;
      } else {
        html += `<div class="card"><div class="table-wrapper"><table>
          <thead><tr>
            <th>时间</th><th>平台</th><th>账号ID</th><th>动作</th><th>状态</th><th>耗时</th><th>响应/错误</th>
          </tr></thead><tbody>
          ${logs.map(l => {
            const statusClass = l.status === 'success' ? 'badge-success' : 'badge-danger';
            const statusLabel = l.status === 'success' ? '成功' : '失败';
            return `<tr>
              <td style="font-size:12px;color:var(--text-secondary)">${new Date(l.created_at).toLocaleString('zh-CN')}</td>
              <td><span class="platform-badge plat-${l.platform}">${l.platform}</span></td>
              <td>${l.account_id}</td>
              <td>${l.action === 'publish' ? '发布' : l.action}</td>
              <td><span class="badge ${statusClass}">${statusLabel}</span></td>
              <td>${l.duration_ms}ms</td>
              <td style="font-size:12px;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                ${l.error_message || JSON.stringify(l.platform_response || '').slice(0, 80)}
              </td>
            </tr>`;
          }).join('')}
          </tbody></table></div></div>`;
      }

      main.innerHTML = html;
    } catch (e) {
      main.innerHTML = `<div class="empty-state">加载失败: ${e.message}</div>`;
    }
  }

  return { render };
})();
