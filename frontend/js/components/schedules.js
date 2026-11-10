/**
 * Schedules view - view and manage scheduled tasks.
 */
const SchedulesView = (() => {
  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const data = await API.listSchedules();
      const schedules = data.schedules;

      let html = `
        <div class="page-header">
          <h2>定时任务</h2>
        </div>
      `;

      if (schedules.length === 0) {
        html += `<div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <p>暂无定时任务</p>
        </div>`;
      } else {
        html += `<div class="card"><div class="table-wrapper"><table>
          <thead><tr>
            <th>ID</th><th>平台</th><th>内容ID</th><th>计划时间</th><th>状态</th><th>重试</th><th>错误信息</th>
          </tr></thead><tbody>
          ${schedules.map(s => {
            const statusClass = s.status === 'done' ? 'badge-done' : s.status === 'failed' ? 'badge-failed' : s.status === 'publishing' ? 'badge-warning' : 'badge-pending';
            const statusLabel = s.status === 'done' ? '已完成' : s.status === 'failed' ? '失败' : s.status === 'publishing' ? '发布中' : '等待中';
            return `<tr>
              <td>${s.id}</td>
              <td><span class="platform-badge plat-${s.platform}">${s.platform}</span></td>
              <td>${s.content_id}</td>
              <td style="font-size:12px;color:var(--text-secondary)">${new Date(s.scheduled_at).toLocaleString('zh-CN')}</td>
              <td><span class="badge ${statusClass}">${statusLabel}</span></td>
              <td>${s.retry_count}</td>
              <td style="font-size:12px;color:var(--danger);max-width:200px;overflow:hidden;text-overflow:ellipsis">${s.last_error || '-'}</td>
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
