/**
 * Accounts management view - matrix system with groups, batch ops, QR login.
 */
const AccountsView = (() => {
  let currentPlatform = '';
  let currentGroupId = null;
  let currentTag = '';
  let currentHealth = '';
  let currentSearch = '';
  let selectedIds = new Set();
  let allAccounts = [];
  let allGroups = [];

  const PLATFORM_ICONS = {
    weibo: 'Wb', wechat: 'Wx', douyin: 'Dy', xiaohongshu: 'Xhs', bilibili: 'Bz'
  };

  const HEALTH_LABELS = { healthy: '正常', warning: '警告', error: '异常', unknown: '未知' };

  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const params = {};
      if (currentPlatform) params.platform = currentPlatform;
      if (currentGroupId !== null) params.group_id = currentGroupId;
      if (currentTag) params.tag = currentTag;
      if (currentHealth) params.health_status = currentHealth;
      if (currentSearch) params.search = currentSearch;

      const [platformsData, accountsData, groupsData] = await Promise.all([
        API.listPlatforms(),
        API.listAccounts(params),
        API.listGroups(),
      ]);
      const platforms = platformsData.platforms;
      allAccounts = accountsData.accounts;
      allGroups = groupsData.groups;

      let html = '<div class="accounts-layout">';

      // ── Left Panel: Groups ──────────────────────────────────
      html += '<div class="accounts-sidebar">';
      html += '<div class="accounts-sidebar-header"><strong>账号分组</strong>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.showAddGroupModal()" title="添加分组">+</button></div>';

      html += '<div class="group-tree">';
      html += '<div class="group-item ' + (currentGroupId === null && !currentPlatform ? 'active' : '') + '" onclick="AccountsView.filterByGroup(null)">全部账号 <span class="group-count">' + allAccounts.length + '</span></div>';
      for (const g of allGroups) {
        html += '<div class="group-item ' + (currentGroupId === g.id ? 'active' : '') + '" onclick="AccountsView.filterByGroup(' + g.id + ')">';
        html += '<span class="group-dot" style="background:' + (g.color || '#3699ff') + '"></span>' + escapeHtml(g.name);
        html += '<span class="group-count">' + g.account_count + '</span>';
        html += '<span class="group-actions">';
        html += '<button class="btn-icon" onclick="event.stopPropagation();AccountsView.showEditGroupModal(' + g.id + ')" title="编辑">&#9998;</button>';
        html += '<button class="btn-icon" onclick="event.stopPropagation();AccountsView.deleteGroup(' + g.id + ')" title="删除">&#10005;</button>';
        html += '</span></div>';
      }
      html += '</div>';

      // Platform filter
      html += '<div class="accounts-sidebar-header" style="margin-top:12px"><strong>平台筛选</strong></div>';
      html += '<div class="platform-filter-list">';
      html += '<div class="pf-item ' + (!currentPlatform ? 'active' : '') + '" onclick="AccountsView.filterByPlatform(\'\')">全部</div>';
      for (const p of platforms) {
        const count = allAccounts.filter(a => a.platform === p.key).length;
        html += '<div class="pf-item ' + (currentPlatform === p.key ? 'active' : '') + '" onclick="AccountsView.filterByPlatform(\'' + p.key + '\')">' + p.name + ' <span>' + count + '</span></div>';
      }
      html += '</div>';

      // Import/Export
      html += '<div style="padding:8px 0">';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.importAccounts()" style="width:100%;margin-bottom:4px">&#128229; 导入账号</button>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.exportAccounts()" style="width:100%">&#128228; 导出账号</button>';
      html += '</div>';

      html += '</div>'; // end sidebar

      // ── Right Panel: Table ──────────────────────────────────
      html += '<div class="accounts-main">';

      // Toolbar
      html += '<div class="accounts-toolbar">';
      html += '<div class="toolbar-left">';
      html += '<h2>账号管理 <span class="count-badge">' + allAccounts.length + '</span></h2>';
      html += '<input class="form-control search-input" type="text" placeholder="搜索昵称/用户名..." value="' + escapeHtml(currentSearch) + '" oninput="AccountsView.filterBySearch(this.value)">';
      html += '<select class="form-control health-filter" onchange="AccountsView.filterByHealth(this.value)">';
      html += '<option value="">全部状态</option>';
      html += '<option value="healthy" ' + (currentHealth === 'healthy' ? 'selected' : '') + '>健康</option>';
      html += '<option value="warning" ' + (currentHealth === 'warning' ? 'selected' : '') + '>警告</option>';
      html += '<option value="error" ' + (currentHealth === 'error' ? 'selected' : '') + '>异常</option>';
      html += '</select>';
      html += '</div>';
      html += '<div class="toolbar-right">';
      html += '<button class="btn btn-primary" onclick="AccountsView.showAddModal()">+ 添加账号</button>';
      html += '</div></div>';

      // Batch action bar
      html += '<div class="batch-bar" id="batch-bar" style="display:none">';
      html += '<span id="batch-count">已选 0 项</span>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.batchVerify()">批量验证</button>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.batchHealthCheck()">健康检查</button>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.batchMove()">移动到分组</button>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.batchTag()">标签管理</button>';
      html += '<button class="btn btn-sm btn-danger" onclick="AccountsView.batchDelete()">批量删除</button>';
      html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.clearSelection()">取消选择</button>';
      html += '</div>';

      // Table
      if (allAccounts.length === 0) {
        html += '<div class="empty-state"><p>暂无账号</p><p style="font-size:13px;color:#7e8299">点击「添加账号」或「导入账号」开始</p></div>';
      } else {
        html += '<div class="table-wrapper"><table class="accounts-table"><thead><tr>';
        html += '<th><input type="checkbox" onchange="AccountsView.toggleAll(this)" id="select-all"></th>';
        html += '<th>平台</th><th>昵称</th><th>用户名</th><th>登录方式</th><th>分组</th><th>标签</th><th>健康</th><th>状态</th><th>操作</th></tr></thead><tbody>';

        for (const a of allAccounts) {
          const checked = selectedIds.has(a.id) ? 'checked' : '';
          const groupName = a.group_id ? (allGroups.find(g => g.id === a.group_id) ? (allGroups.find(g => g.id === a.group_id).name) : '-') : '-';
          const healthClass = 'health-' + (a.health_status || 'unknown');
          const healthLabel = HEALTH_LABELS[a.health_status] || '未知';
          const statusClass = a.status === 'active' ? 'badge-active' : a.status === 'error' ? 'badge-danger' : 'badge-draft';
          const statusLabel = a.status === 'active' ? '正常' : a.status === 'error' ? '异常' : a.status;
          const credTypeLabel = a.credential_type === 'password' ? '密码' : a.credential_type === 'qr' ? '扫码' : a.credential_type === 'token' ? 'Token' : 'Cookie';
          const tags = (a.tags || []).map(function(t) { return '<span class="tag-chip">' + escapeHtml(t) + '</span>'; }).join('');

          html += '<tr>';
          html += '<td><input type="checkbox" ' + checked + ' onchange="AccountsView.toggleOne(' + a.id + ', this)" class="acct-check"></td>';
          html += '<td><span class="platform-badge plat-' + a.platform + '">' + (PLATFORM_ICONS[a.platform] || a.platform) + '</span></td>';
          html += '<td><strong>' + escapeHtml(a.nickname || '-') + '</strong></td>';
          html += '<td style="font-size:12px;color:var(--text-secondary)">' + escapeHtml(a.username || '-') + '</td>';
          html += '<td><span class="badge badge-draft">' + credTypeLabel + '</span></td>';
          html += '<td style="font-size:12px">' + escapeHtml(groupName) + '</td>';
          html += '<td>' + tags + '</td>';
          html += '<td><span class="health-dot ' + healthClass + '" title="' + healthLabel + '"></span> ' + healthLabel + '</td>';
          html += '<td><span class="badge ' + statusClass + '">' + statusLabel + '</span></td>';
          html += '<td><div class="btn-group">';
          html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.verifyAccount(' + a.id + ')">验证</button>';
          html += '<button class="btn btn-sm btn-outline" onclick="AccountsView.showEditModal(' + a.id + ')">编辑</button>';
          html += '<button class="btn btn-sm btn-danger" onclick="AccountsView.deleteAccount(' + a.id + ')">删除</button>';
          html += '</div></td></tr>';
        }
        html += '</tbody></table></div>';
      }

      html += '</div></div>';
      main.innerHTML = html;
      updateBatchBar();
    } catch (e) {
      main.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
    }
  }

  function updateBatchBar() {
    const bar = document.getElementById('batch-bar');
    const cnt = document.getElementById('batch-count');
    if (bar && cnt) {
      bar.style.display = selectedIds.size > 0 ? 'flex' : 'none';
      cnt.textContent = '已选 ' + selectedIds.size + ' 项';
    }
  }

  // ── Filtering ────────────────────────────────────────────────
  function filterByGroup(gid) { currentGroupId = gid; currentPlatform = ''; render(); }
  function filterByPlatform(plat) { currentPlatform = plat; currentGroupId = null; render(); }
  function filterBySearch(val) { currentSearch = val; render(); }
  function filterByHealth(val) { currentHealth = val; render(); }

  // ── Selection ────────────────────────────────────────────────
  function toggleAll(cb) {
    allAccounts.forEach(a => { if (cb.checked) selectedIds.add(a.id); else selectedIds.delete(a.id); });
    updateBatchBar();
  }
  function toggleOne(id, cb) {
    if (cb.checked) selectedIds.add(id); else selectedIds.delete(id);
    updateBatchBar();
  }
  function clearSelection() { selectedIds.clear(); render(); }

  // ── QR State ─────────────────────────────────────────────────
  let qrSessionToken = null;
  let qrPollTimer = null;

  // ── Add Account Modal ────────────────────────────────────────
  async function showAddModal() {
    const platforms = (await API.listPlatforms()).platforms;
    const groups = (await API.listGroups()).groups;

    showModal('添加账号',
      '<div class="form-group"><label>平台</label><select class="form-control" id="add-platform" onchange="AccountsView.onPlatformChange()">' +
      platforms.map(p => '<option value="' + p.key + '">' + p.name + '</option>').join('') +
      '</select></div>' +
      '<div class="form-group"><label>登录方式</label>' +
      '<div class="method-tabs" id="add-method-tabs">' +
      '<button class="method-tab active" data-method="password" onclick="AccountsView.switchLoginMethod(\'password\')">密码登录</button>' +
      '<button class="method-tab" data-method="qr" onclick="AccountsView.switchLoginMethod(\'qr\')">扫码登录</button>' +
      '<button class="method-tab" data-method="cookie" onclick="AccountsView.switchLoginMethod(\'cookie\')">Cookie</button>' +
      '</div></div>' +
      '<div id="add-cred-fields"></div>' +
      '<div id="qr-login-area" style="display:none">' +
      '<div style="text-align:center;margin:12px 0"><img id="qr-image" src="" style="width:180px;height:180px;border:1px solid var(--border);border-radius:8px"><p style="font-size:12px;color:var(--text-secondary);margin-top:8px" id="qr-note"></p><div id="qr-status" style="margin-top:4px;font-size:13px">等待扫码...</div></div></div>' +
      '<div class="form-row"><div class="form-group"><label>昵称 (可选)</label><input class="form-control" id="add-nickname" placeholder="留空则自动获取"></div>' +
      '<div class="form-group"><label>分组</label><select class="form-control" id="add-group"><option value="">无分组</option>' +
      groups.map(g => '<option value="' + g.id + '">' + escapeHtml(g.name) + '</option>').join('') +
      '</select></div></div>' +
      '<div class="form-group"><label>标签 (逗号分隔)</label><input class="form-control" id="add-tags" placeholder="例如: 产品A, 营销号, 主账号"></div>',
    '确认添加', async () => {
      const plat = document.getElementById('add-platform').value;
      const nickname = document.getElementById('add-nickname').value;
      const groupId = document.getElementById('add-group').value;
      const tagsRaw = document.getElementById('add-tags').value;
      const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : [];
      const method = (document.querySelector('.method-tab.active') || {}).dataset ? (document.querySelector('.method-tab.active').dataset.method || 'password') : 'password';
      let credentials = {};
      if (method === 'password') {
        const u = document.getElementById('add-cred-username');
        const p = document.getElementById('add-cred-password');
        if (u && p) credentials = { username: u.value, password: p.value };
      } else if (method === 'qr') {
        if (!qrSessionToken) { toast('请先确认扫码', 'error'); return; }
        credentials = { qr_session_token: qrSessionToken };
      } else {
        const c = document.getElementById('add-cred-cookies');
        if (c) credentials = { cookies: c.value };
      }
      try {
        await API.createAccount({
          platform: plat, credentials, nickname,
          credential_type: method, group_id: groupId ? parseInt(groupId) : null, tags
        });
        toast('账号添加成功', 'success');
        closeModal();
        stopQrPolling();
        render();
      } catch (e) { toast(e.message, 'error'); }
    });

    onPlatformChange();
  }

  async function onPlatformChange() {
    const plat = document.getElementById('add-platform') ? document.getElementById('add-platform').value : '';
    if (!plat) return;
    const methodEl = document.querySelector('.method-tab.active');
    const method = (methodEl && methodEl.dataset) ? methodEl.dataset.method || 'password' : 'password';
    renderCredFields(plat, method);
  }

  async function switchLoginMethod(method) {
    document.querySelectorAll('.method-tab').forEach(function(t) { t.classList.toggle('active', t.dataset.method === method); });
    const platEl = document.getElementById('add-platform');
    const plat = platEl ? platEl.value : '';
    if (plat) { stopQrPolling(); renderCredFields(plat, method); }
  }

  async function renderCredFields(plat, method) {
    const container = document.getElementById('add-cred-fields');
    const qrArea = document.getElementById('qr-login-area');
    stopQrPolling();
    if (method === 'qr') {
      if (container) container.innerHTML = '';
      if (qrArea) qrArea.style.display = 'block';
      try {
        const resp = await fetch('/api/auth/qr/request', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API.getToken() },
          body: JSON.stringify({ platform: plat })
        }).then(r => r.json());
        if (resp.success) {
          document.getElementById('qr-image').src = resp.qr_url;
          document.getElementById('qr-note').textContent = resp.note || '';
          qrSessionToken = resp.session_token;
          document.getElementById('qr-status').innerHTML = '<span style="color:#ffa800">⏳ 等待扫码...</span>';
          qrPollTimer = setInterval(async () => {
            try {
              const s = await fetch('/api/auth/qr/status/' + qrSessionToken).then(r => r.json());
              if (s.status === 'confirmed') {
                document.getElementById('qr-status').innerHTML = '<span style="color:#1bc5bd">✅ 扫码成功！点击确认添加</span>';
                clearInterval(qrPollTimer);
              } else if (s.status === 'expired') {
                document.getElementById('qr-status').innerHTML = '<span style="color:#f64e60">❌ 二维码已过期</span>';
                clearInterval(qrPollTimer);
              }
            } catch (e) { /* ignore */ }
          }, 3000);
        }
      } catch (e) {
        if (qrArea) qrArea.style.display = 'none';
      }
    } else {
      if (qrArea) qrArea.style.display = 'none';
      try {
        const resp = await fetch('/api/auth/credential-fields/' + plat + '/' + method).then(r => r.json());
        const fields = resp.fields || [];
        if (container) container.innerHTML = fields.map(function(f) {
          return '<div class="form-group"><label>' + f.label + (f.required ? ' *' : '') + '</label>' +
            (f.type === 'textarea'
              ? '<textarea class="form-control" id="add-cred-' + f.key + '" rows="4"></textarea>'
              : '<input class="form-control" type="' + f.type + '" id="add-cred-' + f.key + '">') +
            '</div>';
        }).join('');
      } catch (e) {
        if (container) container.innerHTML = '<p style="color:var(--danger)">加载表单字段失败</p>';
      }
    }
  }

  function stopQrPolling() { if (qrPollTimer) { clearInterval(qrPollTimer); qrPollTimer = null; } qrSessionToken = null; }

  // ── Edit Modal ───────────────────────────────────────────────
  async function showEditModal(accountId) {
    const account = await API.getAccount(accountId);
    const groups = (await API.listGroups()).groups;
    showModal('编辑账号',
      '<div class="form-group"><label>昵称</label><input class="form-control" id="edit-nickname" value="' + escapeHtml(account.nickname || '') + '"></div>' +
      '<div class="form-group"><label>分组</label><select class="form-control" id="edit-group"><option value="">无分组</option>' +
      groups.map(g => '<option value="' + g.id + '" ' + (account.group_id === g.id ? 'selected' : '') + '>' + escapeHtml(g.name) + '</option>').join('') +
      '</select></div>' +
      '<div class="form-group"><label>标签 (逗号分隔)</label><input class="form-control" id="edit-tags" value="' + escapeHtml((account.tags || []).join(', ')) + '"></div>',
    '保存', async () => {
      const nickname = document.getElementById('edit-nickname').value;
      const groupId = document.getElementById('edit-group').value;
      const tagsRaw = document.getElementById('edit-tags').value;
      const tags = tagsRaw ? tagsRaw.split(',').map(function(t) { return t.trim(); }).filter(Boolean) : [];
      await API.updateAccount(accountId, { nickname, group_id: groupId ? parseInt(groupId) : null, tags });
      toast('更新成功', 'success');
      closeModal();
      render();
    });
  }

  // ── Account Actions ──────────────────────────────────────────
  async function verifyAccount(accountId) {
    try {
      const result = await API.verifyAccount(accountId);
      toast(result.success ? '验证成功: ' + (result.nickname || '') : '验证失败: ' + result.error, result.success ? 'success' : 'error');
      render();
    } catch (e) { toast(e.message, 'error'); }
  }
  async function deleteAccount(accountId) {
    if (!confirm('确定要删除此账号？')) return;
    try { await API.deleteAccount(accountId); selectedIds.delete(accountId); toast('账号已删除', 'success'); render(); } catch (e) { toast(e.message, 'error'); }
  }

  // ── Batch Actions ────────────────────────────────────────────
  function getSelectedIds() { return Array.from(selectedIds); }
  async function batchVerify() {
    const ids = getSelectedIds(); if (!ids.length) return;
    try {
      const r = await fetch('/api/accounts/batch/verify', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API.getToken() },
        body: JSON.stringify({ account_ids: ids })
      }).then(r => r.json());
      toast('验证完成: ' + r.success_count + '/' + r.total + ' 成功', 'success'); render();
    } catch (e) { toast(e.message, 'error'); }
  }
  async function batchHealthCheck() {
    const ids = getSelectedIds(); if (!ids.length) return;
    try {
      const r = await fetch('/api/accounts/batch/health-check', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API.getToken() },
        body: JSON.stringify({ account_ids: ids })
      }).then(r => r.json());
      toast('健康检查: ' + r.healthy + '/' + r.total + ' 健康', 'success'); render();
    } catch (e) { toast(e.message, 'error'); }
  }
  async function batchMove() {
    const groups = (await API.listGroups()).groups;
    const ids = getSelectedIds(); if (!ids.length) return;
    showModal('移动到分组',
      '<div class="form-group"><label>选择目标分组</label><select class="form-control" id="batch-move-group"><option value="">无分组</option>' +
      groups.map(g => '<option value="' + g.id + '">' + escapeHtml(g.name) + '</option>').join('') +
      '</select></div>', '确认移动', async () => {
        const gid = document.getElementById('batch-move-group').value;
        await fetch('/api/accounts/batch/move', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API.getToken() },
          body: JSON.stringify({ account_ids: ids, group_id: gid ? parseInt(gid) : null })
        }).then(r => r.json());
        toast('移动完成', 'success'); closeModal(); render();
      });
  }
  async function batchTag() {
    const ids = getSelectedIds(); if (!ids.length) return;
    showModal('标签管理',
      '<div class="form-group"><label>标签 (逗号分隔)</label><input class="form-control" id="batch-tags"></div>' +
      '<div class="form-group"><label>操作</label><select class="form-control" id="batch-tag-action"><option value="add">添加标签</option><option value="remove">移除标签</option></select></div>',
      '确认', async () => {
        const tagsRaw = document.getElementById('batch-tags').value;
        const tags = tagsRaw ? tagsRaw.split(',').map(function(t) { return t.trim(); }).filter(Boolean) : [];
        const action = document.getElementById('batch-tag-action').value;
        await fetch('/api/accounts/batch/tag', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API.getToken() },
          body: JSON.stringify({ account_ids: ids, tags: tags, action: action })
        }).then(r => r.json());
        toast('标签更新完成', 'success'); closeModal(); render();
      });
  }
  async function batchDelete() {
    const ids = getSelectedIds(); if (!ids.length) return;
    if (!confirm('确定要删除 ' + ids.length + ' 个账号？此操作不可撤销。')) return;
    try {
      await fetch('/api/accounts/batch/delete', {
        method: 'DELETE', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API.getToken() },
        body: JSON.stringify({ account_ids: ids })
      }).then(r => r.json());
      selectedIds.clear(); toast('批量删除完成', 'success'); render();
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Group Actions ────────────────────────────────────────────
  async function showAddGroupModal() {
    showModal('添加分组',
      '<div class="form-group"><label>分组名称</label><input class="form-control" id="group-name"></div>' +
      '<div class="form-group"><label>描述</label><input class="form-control" id="group-desc"></div>' +
      '<div class="form-group"><label>颜色</label><input class="form-control" type="color" id="group-color" value="#3699ff"></div>',
      '确认添加', async () => {
        try {
          await API.createGroup({
            name: document.getElementById('group-name').value,
            description: document.getElementById('group-desc').value,
            color: document.getElementById('group-color').value,
          });
          toast('分组已创建', 'success'); closeModal(); render();
        } catch (e) { toast(e.message, 'error'); }
      });
  }
  async function showEditGroupModal(gid) {
    const group = allGroups.find(function(g) { return g.id === gid; });
    if (!group) return;
    showModal('编辑分组',
      '<div class="form-group"><label>分组名称</label><input class="form-control" id="group-name" value="' + escapeHtml(group.name) + '"></div>' +
      '<div class="form-group"><label>描述</label><input class="form-control" id="group-desc" value="' + escapeHtml(group.description || '') + '"></div>' +
      '<div class="form-group"><label>颜色</label><input class="form-control" type="color" id="group-color" value="' + (group.color || '#3699ff') + '"></div>',
      '保存', async () => {
        try {
          await API.updateGroup(gid, {
            name: document.getElementById('group-name').value,
            description: document.getElementById('group-desc').value,
            color: document.getElementById('group-color').value,
          });
          toast('分组已更新', 'success'); closeModal(); render();
        } catch (e) { toast(e.message, 'error'); }
      });
  }
  async function deleteGroup(gid) {
    if (!confirm('确定删除此分组？')) return;
    try { await API.deleteGroup(gid); toast('分组已删除', 'success'); render(); } catch (e) { toast(e.message, 'error'); }
  }

  // ── Import / Export ──────────────────────────────────────────
  function importAccounts() {
    var input = document.createElement('input');
    input.type = 'file'; input.accept = '.json';
    input.onchange = async function() {
      var file = input.files[0]; if (!file) return;
      try {
        var formData = new FormData(); formData.append('file', file);
        var resp = await fetch('/api/accounts/batch/import', {
          method: 'POST', headers: { 'Authorization': 'Bearer ' + API.getToken() }, body: formData,
        }).then(function(r) { return r.json(); });
        if (resp.success) {
          toast('导入完成: ' + resp.imported + ' 个账号', 'success');
          if (resp.errors.length) toast('警告: ' + resp.errors.join('; '), 'error');
          render();
        }
      } catch (e) { toast('导入失败: ' + e.message, 'error'); }
    };
    input.click();
  }
  async function exportAccounts() {
    try {
      var resp = await fetch('/api/accounts/batch/export', {
        headers: { 'Authorization': 'Bearer ' + API.getToken() }
      }).then(function(r) { return r.json(); });
      var blob = new Blob([JSON.stringify(resp, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a'); a.href = url;
      a.download = 'accounts_export_' + new Date().toISOString().slice(0, 10) + '.json';
      a.click(); URL.revokeObjectURL(url);
      toast('导出完成', 'success');
    } catch (e) { toast('导出失败: ' + e.message, 'error'); }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div'); div.textContent = str; return div.innerHTML;
  }

  return {
    render: render,
    showAddModal: showAddModal, showEditModal: showEditModal,
    verifyAccount: verifyAccount, deleteAccount: deleteAccount,
    filterByGroup: filterByGroup, filterByPlatform: filterByPlatform,
    filterBySearch: filterBySearch, filterByHealth: filterByHealth,
    toggleAll: toggleAll, toggleOne: toggleOne, clearSelection: clearSelection,
    batchVerify: batchVerify, batchHealthCheck: batchHealthCheck,
    batchMove: batchMove, batchTag: batchTag, batchDelete: batchDelete,
    showAddGroupModal: showAddGroupModal, showEditGroupModal: showEditGroupModal,
    deleteGroup: deleteGroup, importAccounts: importAccounts, exportAccounts: exportAccounts,
    onPlatformChange: onPlatformChange, switchLoginMethod: switchLoginMethod,
  };
})();
