/**
 * Publish workflow - batch publish, smart schedule, queue monitor.
 */
const PublishView = (() => {
  let allAccounts = [];
  let draftContents = [];

  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const [accData, contentData, queueData] = await Promise.all([
        API.listAccounts({}),
        API.listContent({ status: 'draft' }),
        API.listPublishQueue(),
      ]);
      allAccounts = accData.accounts;
      draftContents = contentData.contents;
      const queue = queueData.queue;

      let html = '<div class="page-header"><h2>批量发布</h2></div>';

      // ── Content selector ────────────────────────────────────
      html += '<div class="card" style="margin-bottom:16px"><div class="card-header">选择内容</div><div class="card-body">';
      html += '<div class="form-row"><div class="form-group"><label>使用已有草稿</label><select class="form-control" id="pub-content">';
      html += '<option value="">-- 选择草稿 --</option>' + draftContents.map(function(c) {
        return '<option value="' + c.id + '">[' + c.platform + '] ' + escapeHtml(c.title || '(无标题)') + '</option>';
      }).join('') + '</select></div>';
      html += '<div class="form-group"><label>或直接输入</label><input class="form-control" id="pub-text-quick" placeholder="直接输入简短内容..."></div></div>';
      html += '</div></div>';

      // ── Target accounts ─────────────────────────────────────
      var platGroups = {};
      allAccounts.forEach(function(a) {
        if (!platGroups[a.platform]) platGroups[a.platform] = [];
        platGroups[a.platform].push(a);
      });
      var platNames = { xiaohongshu: '小红书', weibo: '微博', bilibili: 'B站', douyin: '抖音', wechat: '微信' };

      html += '<div class="card" style="margin-bottom:16px"><div class="card-header">选择发布目标 <span style="font-size:12px;color:var(--text-secondary)" id="selected-count">已选 0</span></div><div class="card-body">';
      html += '<div class="publish-account-grid">';
      for (var plat in platGroups) {
        var accs = platGroups[plat];
        html += '<div class="publish-plat-group"><div class="publish-plat-header"><span class="platform-badge plat-' + plat + '">' + (platNames[plat] || plat) + '</span><span style="font-size:11px;color:var(--text-secondary)">' + accs.length + '个</span></div>';
        html += accs.map(function(a) {
          return '<label class="publish-account-item"><input type="checkbox" class="pub-target" value="' + a.id + '" data-plat="' + a.platform + '" onchange="PublishView.updateCount()"> ' + escapeHtml(a.nickname || a.username) + '</label>';
        }).join('');
        html += '</div>';
      }
      html += '</div>';
      html += '<div style="margin-top:8px;display:flex;gap:8px">';
      html += '<button class="btn btn-sm btn-outline" onclick="PublishView.selectAll(true)">全选</button>';
      html += '<button class="btn btn-sm btn-outline" onclick="PublishView.selectAll(false)">取消</button></div>';
      html += '</div></div>';

      // ── Action buttons ──────────────────────────────────────
      html += '<div style="display:flex;gap:10px;margin-bottom:24px">';
      html += '<button class="btn btn-success" onclick="PublishView.doBatchPublish()">&#128640; 立即发布到所选账号</button>';
      html += '<button class="btn btn-primary" onclick="PublishView.doSmartSchedule()">&#128197; 智能定时发布</button>';
      html += '<button class="btn btn-outline" onclick="PublishView.showManualSchedule()">&#128339; 手动指定时间</button>';
      html += '</div>';

      // ── Queue ──────────────────────────────────────────────
      html += '<div class="card"><div class="card-header">发布队列</div><div class="card-body">';
      if (queue.length === 0) {
        html += '<div class="empty-state" style="padding:20px">暂无发布任务</div>';
      } else {
        html += '<div class="table-wrapper"><table><thead><tr><th>类型</th><th>平台</th><th>账号</th><th>计划时间</th><th>状态</th><th>详情</th><th>操作</th></tr></thead><tbody>';
        html += queue.map(function(item) {
          var statusClass, statusLabel;
          if (item.status === 'done' || item.status === 'success') { statusClass = 'badge-done'; statusLabel = '完成'; }
          else if (item.status === 'failed') { statusClass = 'badge-failed'; statusLabel = '失败'; }
          else if (item.status === 'publishing') { statusClass = 'badge-warning'; statusLabel = '发布中'; }
          else { statusClass = 'badge-pending'; statusLabel = '等待中'; }

          var actions = '';
          if (item.type === 'schedule' && item.status === 'failed') {
            actions = '<button class="btn btn-sm btn-outline" onclick="PublishView.retrySchedule(' + item.id + ')">重试</button>';
          }
          if (item.type === 'schedule' && (item.status === 'pending' || item.status === 'failed')) {
            actions += '<button class="btn btn-sm btn-danger" onclick="PublishView.cancelSchedule(' + item.id + ')" style="margin-left:4px">取消</button>';
          }

          var timeStr = item.scheduled_at ? new Date(item.scheduled_at).toLocaleString('zh-CN') : (item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : '-');
          var detail = item.type === 'log' ? (item.error_message || '') + ' (' + (item.duration_ms || 0) + 'ms)' : (item.last_error || '重试 ' + item.retry_count + '/' + item.max_retries);

          return '<tr><td>' + (item.type === 'schedule' ? '&#128197; 定时' : '&#128640; 即时') + '</td>' +
            '<td><span class="platform-badge plat-' + item.platform + '">' + item.platform + '</span></td>' +
            '<td>' + escapeHtml(item.nickname || '') + '</td>' +
            '<td style="font-size:12px">' + timeStr + '</td>' +
            '<td><span class="badge ' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td style="font-size:12px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + escapeHtml(detail) + '</td>' +
            '<td>' + actions + '</td></tr>';
        }).join('');
        html += '</tbody></table></div>';
      }
      html += '</div></div>';

      main.innerHTML = html;
    } catch (e) {
      main.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
    }
  }

  function updateCount() {
    var count = document.querySelectorAll('.pub-target:checked').length;
    var el = document.getElementById('selected-count');
    if (el) el.textContent = '已选 ' + count;
  }

  function selectAll(sel) {
    document.querySelectorAll('.pub-target').forEach(function(cb) { cb.checked = sel; });
    updateCount();
  }

  function getSelected() {
    return Array.from(document.querySelectorAll('.pub-target:checked')).map(function(cb) { return parseInt(cb.value); });
  }

  async function getContentId() {
    var selectVal = document.getElementById('pub-content').value;
    if (selectVal) return parseInt(selectVal);

    var quickText = document.getElementById('pub-text-quick').value.trim();
    if (!quickText) return null;

    var selected = getSelected();
    if (selected.length === 0) return null;

    var result = await API.createContent({
      account_id: selected[0],
      content_type: 'text',
      title: quickText.substring(0, 50),
      text: quickText,
      tags: [],
    });
    return result.content.id;
  }

  async function doBatchPublish() {
    var selected = getSelected();
    if (selected.length === 0) { toast('请选择发布目标', 'error'); return; }

    var contentId = await getContentId();
    if (!contentId) { toast('请选择内容或输入正文', 'error'); return; }

    try {
      var result = await API.batchPublish({ content_id: contentId, account_ids: selected });
      toast('发布完成: ' + result.success_count + ' 成功, ' + result.fail_count + ' 失败', result.fail_count > 0 ? 'error' : 'success');
      render();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function doSmartSchedule() {
    var selected = getSelected();
    if (selected.length === 0) { toast('请选择发布目标', 'error'); return; }

    var contentId = await getContentId();
    if (!contentId) { toast('请选择内容或输入正文', 'error'); return; }

    try {
      var result = await API.smartSchedule({ content_id: contentId, account_ids: selected });
      var msg = '智能排期完成: ' + result.total + ' 个任务\n';
      result.scheduled.forEach(function(s) {
        msg += s.platform + ' -> ' + new Date(s.scheduled_at).toLocaleString('zh-CN') + '\n';
      });
      toast(msg, 'success');
      render();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function showManualSchedule() {
    var selected = getSelected();
    if (selected.length === 0) { toast('请选择发布目标', 'error'); return; }

    showModal('手动定时发布',
      '<div class="form-group"><label>发布时间</label><input class="form-control" type="datetime-local" id="manual-dt"></div>' +
      '<p style="font-size:12px;color:var(--text-secondary)">将为 ' + selected.length + ' 个账号创建定时任务</p>',
      '确认定时', async function() {
        var dtVal = document.getElementById('manual-dt').value;
        if (!dtVal) { toast('请选择时间', 'error'); return; }
        var contentId = await getContentId();
        if (!contentId) { toast('请选择内容或输入正文', 'error'); return; }
        try {
          await API.scheduleContent(contentId, new Date(dtVal).toISOString(), selected);
          toast('定时任务已创建', 'success');
          closeModal();
          render();
        } catch (e) { toast(e.message, 'error'); }
      });
  }

  async function retrySchedule(id) {
    try {
      var result = await API.retrySchedule(id);
      toast(result.success ? '重试成功' : '重试失败: ' + result.error, result.success ? 'success' : 'error');
      render();
    } catch (e) { toast(e.message, 'error'); }
  }

  async function cancelSchedule(id) {
    if (!confirm('确定取消此定时任务？')) return;
    try {
      await API.cancelSchedule(id);
      toast('任务已取消', 'success');
      render();
    } catch (e) { toast(e.message, 'error'); }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return {
    render: render,
    updateCount: updateCount,
    selectAll: selectAll,
    doBatchPublish: doBatchPublish,
    doSmartSchedule: doSmartSchedule,
    showManualSchedule: showManualSchedule,
    retrySchedule: retrySchedule,
    cancelSchedule: cancelSchedule,
  };
})();
