/**
 * Content management view - content list, media library, AI creator, templates.
 */
const ContentView = (() => {
  let currentTab = 'list';
  let allAccounts = [];

  const TABS = [
    { key: 'list', label: '内容列表', icon: '&#128196;' },
    { key: 'media', label: '素材库', icon: '&#128247;' },
    { key: 'ai', label: 'AI 创作', icon: '&#129302;' },
    { key: 'templates', label: '模板管理', icon: '&#128203;' },
  ];

  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const accData = await API.listAccounts({});
      allAccounts = accData.accounts;

      let html = '<div class="page-header"><h2>内容管理</h2></div>';
      html += '<div class="tabs">' + TABS.map(function(t) {
        return '<div class="tab ' + (currentTab === t.key ? 'active' : '') + '" onclick="ContentView.switchTab(\'' + t.key + '\')">' + t.icon + ' ' + t.label + '</div>';
      }).join('') + '</div>';

      main.innerHTML = html;
      await switchTab(currentTab);
    } catch (e) {
      main.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
    }
  }

  async function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(function(el) {
      el.classList.toggle('active', el.textContent.includes(TABS.find(function(t) { return t.key === tab; }).label));
    });
    if (tab === 'list') await renderContentList();
    else if (tab === 'media') await renderMediaLibrary();
    else if (tab === 'ai') await renderAICreator();
    else if (tab === 'templates') await renderTemplates();
  }

  // ── Tab: Content List ─────────────────────────────────────────
  async function renderContentList() {
    const main = document.getElementById('main-content');
    var existing = main.querySelector('.card');
    if (existing && currentTab === 'list') return; // already rendered

    // Remove old tab content
    var old = main.querySelector('.content-tab-body');
    if (old) old.remove();

    var container = document.createElement('div');
    container.className = 'content-tab-body';

    try {
      const data = await API.listContent();
      const contents = data.contents;

      var html = '<div style="margin-bottom:16px"><button class="btn btn-primary" onclick="ContentView.showCreateModal()">+ 新建内容</button></div>';

      if (contents.length === 0) {
        html += '<div class="empty-state"><p>暂无内容，点击上方按钮创建</p></div>';
      } else {
        html += '<div class="card"><div class="table-wrapper"><table><thead><tr>';
        html += '<th>标题</th><th>平台</th><th>类型</th><th>状态</th><th>文本</th><th>时间</th><th>操作</th>';
        html += '</tr></thead><tbody>';
        html += contents.map(function(c) {
          var statusClass = 'badge-' + (c.status === 'published' ? 'published' : c.status === 'failed' ? 'failed' : c.status === 'scheduled' ? 'scheduled' : 'draft');
          var statusLabel = c.status === 'published' ? '已发布' : c.status === 'failed' ? '失败' : c.status === 'scheduled' ? '已排期' : '草稿';
          var textPreview = (c.text || '-').substring(0, 80);
          return '<tr><td><strong>' + escapeHtml(c.title || '(无标题)') + '</strong></td>' +
            '<td><span class="platform-badge plat-' + c.platform + '">' + c.platform + '</span></td>' +
            '<td>' + c.content_type + '</td>' +
            '<td><span class="badge ' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td style="font-size:12px;color:var(--text-secondary);max-width:200px">' + escapeHtml(textPreview) + '</td>' +
            '<td style="font-size:12px;color:var(--text-secondary)">' + new Date(c.created_at).toLocaleString('zh-CN') + '</td>' +
            '<td><div class="btn-group">' +
            (c.status !== 'published' ? '<button class="btn btn-sm btn-success" onclick="ContentView.showPublishModal(' + c.id + ')">发布</button>' : '') +
            '<button class="btn btn-sm btn-outline" onclick="ContentView.showEditModal(' + c.id + ')">编辑</button>' +
            '<button class="btn btn-sm btn-danger" onclick="ContentView.deleteContent(' + c.id + ')">删除</button>' +
            '</div></td></tr>';
        }).join('');
        html += '</tbody></table></div></div>';
      }
      container.innerHTML = html;
      main.appendChild(container);
    } catch (e) {
      container.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
      main.appendChild(container);
    }
  }

  // ── Tab: Media Library ────────────────────────────────────────
  async function renderMediaLibrary() {
    const main = document.getElementById('main-content');
    var old = main.querySelector('.content-tab-body');
    if (old) old.remove();

    var container = document.createElement('div');
    container.className = 'content-tab-body';

    try {
      const data = await API.listMedia();
      const assets = data.assets;

      var html = '<div style="margin-bottom:16px;display:flex;gap:8px;align-items:center">';
      html += '<button class="btn btn-primary" onclick="ContentView.uploadMedia()">+ 上传素材</button>';
      html += '<select class="form-control" style="width:120px" onchange="ContentView.filterMedia(this.value)">';
      html += '<option value="">全部类型</option><option value="image">图片</option><option value="video">视频</option></select>';
      html += '<span style="font-size:13px;color:var(--text-secondary)">共 ' + assets.length + ' 个文件</span></div>';

      if (assets.length === 0) {
        html += '<div class="empty-state"><p>暂无上传的素材</p></div>';
      } else {
        html += '<div class="media-grid">';
        html += assets.map(function(a) {
          var sizeMB = (a.file_size / 1024 / 1024).toFixed(2);
          var date = new Date(a.created_at).toLocaleString('zh-CN');
          var isImage = a.media_type === 'image';
          return '<div class="media-card">' +
            (isImage ? '<img src="' + a.file_path + '" class="media-thumb" onerror="this.src=\'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2212%22>无预览</text></svg>\'">' : '<div class="media-thumb media-file-icon">' + (a.media_type === 'video' ? '\u25B6' : '\u266A') + '</div>') +
            '<div class="media-info"><div class="media-name" title="' + escapeHtml(a.filename) + '">' + escapeHtml(a.filename) + '</div>' +
            '<div class="media-meta">' + sizeMB + ' MB &middot; ' + date + '</div></div>' +
            '<button class="media-delete" onclick="ContentView.deleteMedia(' + a.id + ')" title="删除">\u2715</button></div>';
        }).join('');
        html += '</div>';
      }
      container.innerHTML = html;
      main.appendChild(container);
    } catch (e) {
      container.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
      main.appendChild(container);
    }
  }

  function uploadMedia() {
    var input = document.createElement('input');
    input.type = 'file'; input.multiple = true; input.accept = 'image/*,video/*';
    input.onchange = async function() {
      var files = input.files;
      var success = 0;
      for (var i = 0; i < files.length; i++) {
        try {
          var result = await API.uploadFile(files[i]);
          if (result.success) success++;
        } catch (e) { /* continue */ }
      }
      toast('上传完成: ' + success + '/' + files.length, 'success');
      await renderMediaLibrary();
    };
    input.click();
  }

  async function deleteMedia(id) {
    if (!confirm('确定删除此素材？')) return;
    try { await API.deleteMedia(id); toast('素材已删除', 'success'); await renderMediaLibrary(); } catch (e) { toast(e.message, 'error'); }
  }

  async function filterMedia(type) {
    const data = await API.listMedia(type ? { media_type: type } : {});
    var grid = document.querySelector('.media-grid');
    if (!grid) return;
    var html = data.assets.length === 0 ? '<div class="empty-state"><p>暂无素材</p></div>' :
      data.assets.map(function(a) {
        var sizeMB = (a.file_size / 1024 / 1024).toFixed(2);
        var date = new Date(a.created_at).toLocaleString('zh-CN');
        var isImage = a.media_type === 'image';
        return '<div class="media-card">' +
          (isImage ? '<img src="' + a.file_path + '" class="media-thumb" onerror="this.src=\'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23f0f0f0%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2212%22>无预览</text></svg>\'">' : '<div class="media-thumb media-file-icon">' + (a.media_type === 'video' ? '\u25B6' : '\u266A') + '</div>') +
          '<div class="media-info"><div class="media-name">' + escapeHtml(a.filename) + '</div>' +
          '<div class="media-meta">' + sizeMB + ' MB &middot; ' + date + '</div></div>' +
          '<button class="media-delete" onclick="ContentView.deleteMedia(' + a.id + ')">\u2715</button></div>';
      }).join('');
    grid.innerHTML = html;
  }

  // ── Tab: AI Creator ───────────────────────────────────────────
  async function renderAICreator() {
    const main = document.getElementById('main-content');
    var old = main.querySelector('.content-tab-body');
    if (old) old.remove();

    var container = document.createElement('div');
    container.className = 'content-tab-body';

    var html = '<div class="card"><div class="card-body">';
    html += '<div class="form-row"><div class="form-group"><label>目标平台</label><select class="form-control" id="ai-platform">' +
      '<option value="xiaohongshu">小红书</option><option value="weibo">微博</option><option value="bilibili">B站</option><option value="douyin">抖音</option><option value="wechat">微信</option></select></div>' +
      '<div class="form-group"><label>内容类型</label><select class="form-control" id="ai-category"><option value="product">产品测评/推荐</option><option value="knowledge">知识干货</option><option value="lifestyle">生活方式</option><option value="news">行业资讯</option></select></div></div>' +
      '<div class="form-row"><div class="form-group"><label>语气风格</label><select class="form-control" id="ai-tone"><option value="casual">轻松随意</option><option value="professional">专业严谨</option><option value="enthusiastic">热情洋溢</option><option value="informative">干货教程</option></select></div>' +
      '<div class="form-group"><label>内容类型</label><select class="form-control" id="ai-type"><option value="text">纯文本</option><option value="image">图文</option><option value="video">视频</option></select></div></div>' +
      '<div class="form-group"><label>主题 / 关键词</label><input class="form-control" id="ai-topic" placeholder="例如: 新款防晒霜测评, Python入门教程, 周末探店分享..."></div>' +
      '<button class="btn btn-primary" onclick="ContentView.aiGenerate()" id="ai-gen-btn">&#129302; 生成内容</button>' +
      '<button class="btn btn-outline" style="margin-left:8px" onclick="ContentView.aiGenHashtags()"># 只生成标签</button>' +
      '<div id="ai-result" style="margin-top:16px"></div></div></div>';

    container.innerHTML = html;
    main.appendChild(container);
  }

  async function aiGenerate() {
    var topic = document.getElementById('ai-topic').value.trim();
    if (!topic) { toast('请输入主题', 'error'); return; }
    var btn = document.getElementById('ai-gen-btn');
    btn.disabled = true; btn.textContent = '生成中...';

    try {
      var result = await API.aiGenerate({
        platform: document.getElementById('ai-platform').value,
        topic: topic,
        tone: document.getElementById('ai-tone').value,
        category: document.getElementById('ai-category').value,
        content_type: document.getElementById('ai-type').value,
      });
      document.getElementById('ai-result').innerHTML =
        '<div class="card" style="margin-top:0"><div class="card-header">生成结果 - ' + escapeHtml(result.platform) + '</div><div class="card-body">' +
        '<div class="form-group"><label>标题</label><input class="form-control" id="ai-title" value="' + escapeHtml(result.title) + '"></div>' +
        '<div class="form-group"><label>正文</label><textarea class="form-control" id="ai-text" rows="8">' + escapeHtml(result.text) + '</textarea></div>' +
        '<div class="form-group"><label>标签</label><input class="form-control" id="ai-tags" value="' + escapeHtml((result.tags || []).join(' ')) + '"></div>' +
        '<div style="display:flex;gap:8px">' +
        '<button class="btn btn-success" onclick="ContentView.aiSaveContent()">保存为草稿</button>' +
        '<button class="btn btn-outline" onclick="ContentView.aiRegenerate()">重新生成</button></div></div></div>';
    } catch (e) { toast(e.message, 'error'); }
    finally { btn.disabled = false; btn.textContent = '\u{1F916} 生成内容'; }
  }

  async function aiGenHashtags() {
    var topic = document.getElementById('ai-topic').value.trim();
    if (!topic) { toast('请输入主题', 'error'); return; }
    try {
      var result = await API.aiHashtags({
        platform: document.getElementById('ai-platform').value,
        topic: topic, count: 10,
      });
      document.getElementById('ai-result').innerHTML =
        '<div class="card" style="margin-top:0"><div class="card-header">推荐标签</div><div class="card-body">' +
        '<div style="display:flex;flex-wrap:wrap;gap:6px">' + result.tags.map(function(t) { return '<span class="tag-chip">' + t + '</span>'; }).join('') + '</div>' +
        '<p style="font-size:12px;color:var(--text-secondary);margin-top:12px">点击标签可复制到剪贴板</p></div></div>';
    } catch (e) { toast(e.message, 'error'); }
  }

  function aiRegenerate() { aiGenerate(); }

  async function aiSaveContent() {
    var title = document.getElementById('ai-title').value;
    var text = document.getElementById('ai-text').value;
    var tagsRaw = document.getElementById('ai-tags').value;
    var tags = tagsRaw.split(/[#\s]+/).map(function(t) { return t.trim(); }).filter(Boolean);
    var platform = document.getElementById('ai-platform').value;

    if (allAccounts.length === 0) { toast('请先添加账号', 'error'); return; }
    var account = allAccounts.find(function(a) { return a.platform === platform; });
    if (!account) account = allAccounts[0];

    try {
      await API.createContent({
        account_id: account.id, content_type: 'text', title: title, text: text, tags: tags
      });
      toast('草稿已保存', 'success');
    } catch (e) { toast(e.message, 'error'); }
  }

  // ── Tab: Templates ────────────────────────────────────────────
  async function renderTemplates() {
    const main = document.getElementById('main-content');
    var old = main.querySelector('.content-tab-body');
    if (old) old.remove();

    var container = document.createElement('div');
    container.className = 'content-tab-body';

    try {
      const data = await API.listTemplates();
      const templates = data.templates;

      var html = '<div style="margin-bottom:16px"><button class="btn btn-primary" onclick="ContentView.showTemplateModal()">+ 新建模板</button></div>';

      if (templates.length === 0) {
        html += '<div class="empty-state"><p>暂无模板，创建模板可快速复用常用内容格式</p></div>';
      } else {
        html += '<div class="template-grid">';
        html += templates.map(function(t) {
          var platColor = 'plat-' + t.platform;
          return '<div class="template-card"><div class="template-card-header"><span class="platform-badge ' + platColor + '">' + t.platform + '</span><strong>' + escapeHtml(t.name) + '</strong><span class="badge badge-draft">' + (t.category || '通用') + '</span></div>' +
            '<div class="template-preview"><div class="template-field"><label>标题模板</label><code>' + escapeHtml(t.title_template || '-') + '</code></div>' +
            '<div class="template-field"><label>正文模板</label><code>' + escapeHtml((t.body_template || '-').substring(0, 100)) + '</code></div>' +
            '<div class="template-field"><label>标签</label><code>' + escapeHtml(t.hashtag_template || '-') + '</code></div></div>' +
            '<div class="template-actions"><span style="font-size:11px;color:var(--text-secondary)">使用 ' + t.use_count + ' 次</span>' +
            '<div class="btn-group"><button class="btn btn-sm btn-outline" onclick="ContentView.showTemplateModal(' + t.id + ')">编辑</button>' +
            '<button class="btn btn-sm btn-danger" onclick="ContentView.deleteTemplate(' + t.id + ')">删除</button></div></div></div>';
        }).join('');
        html += '</div>';
      }
      container.innerHTML = html;
      main.appendChild(container);
    } catch (e) {
      container.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
      main.appendChild(container);
    }
  }

  async function showTemplateModal(id) {
    var template = id ? (await API.listTemplates()).templates.find(function(t) { return t.id === id; }) : null;
    var title = template ? '编辑模板' : '新建模板';
    showModal(title,
      '<div class="form-group"><label>模板名称</label><input class="form-control" id="tpl-name" value="' + escapeHtml(template ? template.name || '' : '') + '"></div>' +
      '<div class="form-row"><div class="form-group"><label>平台</label><select class="form-control" id="tpl-platform"><option value="xiaohongshu" ' + (template && template.platform === 'xiaohongshu' ? 'selected' : '') + '>小红书</option><option value="weibo" ' + (template && template.platform === 'weibo' ? 'selected' : '') + '>微博</option><option value="bilibili" ' + (template && template.platform === 'bilibili' ? 'selected' : '') + '>B站</option><option value="douyin" ' + (template && template.platform === 'douyin' ? 'selected' : '') + '>抖音</option><option value="wechat" ' + (template && template.platform === 'wechat' ? 'selected' : '') + '>微信</option></select></div>' +
      '<div class="form-group"><label>分类</label><input class="form-control" id="tpl-category" value="' + escapeHtml(template ? template.category || '' : '') + '" placeholder="例如: 产品推广"></div></div>' +
      '<div class="form-group"><label>标题模板</label><input class="form-control" id="tpl-title" value="' + escapeHtml(template ? template.title_template || '' : '') + '" placeholder="使用 {topic} {product} 占位符"></div>' +
      '<div class="form-group"><label>正文模板</label><textarea class="form-control" id="tpl-body" rows="5" placeholder="使用 {topic} {point1} {benefit} 等占位符">' + escapeHtml(template ? template.body_template || '' : '') + '</textarea></div>' +
      '<div class="form-group"><label>标签模板</label><input class="form-control" id="tpl-hashtags" value="' + escapeHtml(template ? template.hashtag_template || '' : '') + '" placeholder="#{topic} #{platform}">',
      '保存', async function() {
        var data = {
          name: document.getElementById('tpl-name').value,
          platform: document.getElementById('tpl-platform').value,
          category: document.getElementById('tpl-category').value,
          title_template: document.getElementById('tpl-title').value,
          body_template: document.getElementById('tpl-body').value,
          hashtag_template: document.getElementById('tpl-hashtags').value,
        };
        try {
          if (template) {
            await API.updateTemplate(id, data);
          } else {
            await API.createTemplate(data);
          }
          toast('模板已保存', 'success');
          closeModal();
          await renderTemplates();
        } catch (e) { toast(e.message, 'error'); }
      });
  }

  async function deleteTemplate(id) {
    if (!confirm('确定删除此模板？')) return;
    try { await API.deleteTemplate(id); toast('模板已删除', 'success'); await renderTemplates(); } catch (e) { toast(e.message, 'error'); }
  }

  // ── Content CRUD (existing) ───────────────────────────────────
  async function showCreateModal() {
    if (allAccounts.length === 0) { toast('请先添加账号', 'error'); return; }
    showModal('新建内容',
      '<div class="form-group"><label>选择账号</label><select class="form-control" id="create-account">' +
      allAccounts.map(function(a) { return '<option value="' + a.id + '">[' + a.platform + '] ' + escapeHtml(a.nickname || a.username) + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="form-group"><label>内容类型</label><select class="form-control" id="create-type"><option value="text">纯文本</option><option value="image">图文</option><option value="video">视频</option><option value="article">文章</option></select></div>' +
      '<div class="form-group"><label>标题</label><input class="form-control" id="create-title"></div>' +
      '<div class="form-group"><label>正文</label><textarea class="form-control" id="create-text" rows="5"></textarea></div>' +
      '<div class="form-group"><label>标签 (逗号分隔)</label><input class="form-control" id="create-tags"></div>' +
      '<div class="form-group"><label>定时发布 (可选)</label><input class="form-control" type="datetime-local" id="create-schedule"></div>',
      '创建', async function() {
        var data = {
          account_id: parseInt(document.getElementById('create-account').value),
          content_type: document.getElementById('create-type').value,
          title: document.getElementById('create-title').value,
          text: document.getElementById('create-text').value,
          tags: document.getElementById('create-tags').value.split(',').map(function(t) { return t.trim(); }).filter(Boolean),
        };
        var sched = document.getElementById('create-schedule').value;
        if (sched) data.schedule_at = new Date(sched).toISOString();
        try { await API.createContent(data); toast('创建成功', 'success'); closeModal(); await renderContentList(); } catch (e) { toast(e.message, 'error'); }
      });
  }

  async function showEditModal(contentId) {
    var content = await API.getContent(contentId);
    showModal('编辑内容',
      '<div class="form-group"><label>标题</label><input class="form-control" id="edit-title" value="' + escapeHtml(content.title || '') + '"></div>' +
      '<div class="form-group"><label>正文</label><textarea class="form-control" id="edit-text" rows="5">' + escapeHtml(content.text || '') + '</textarea></div>' +
      '<div class="form-group"><label>标签 (逗号分隔)</label><input class="form-control" id="edit-tags" value="' + escapeHtml((content.tags || []).join(', ')) + '"></div>',
      '保存', async function() {
        var data = {
          title: document.getElementById('edit-title').value,
          text: document.getElementById('edit-text').value,
          tags: document.getElementById('edit-tags').value.split(',').map(function(t) { return t.trim(); }).filter(Boolean),
        };
        try { await API.updateContent(contentId, data); toast('已更新', 'success'); closeModal(); await renderContentList(); } catch (e) { toast(e.message, 'error'); }
      });
  }

  async function showPublishModal(contentId) {
    if (allAccounts.length === 0) { toast('没有可用的账号', 'error'); return; }
    showModal('选择发布目标',
      '<p style="margin-bottom:12px;font-size:13px;color:var(--text-secondary)">选择要发布到的账号：</p>' +
      allAccounts.map(function(a) { return '<label style="display:block;padding:6px 0;cursor:pointer"><input type="radio" name="publish-account" value="' + a.id + '"> <span class="platform-badge plat-' + a.platform + '">' + a.platform + '</span> <strong>' + escapeHtml(a.nickname || a.username) + '</strong></label>'; }).join(''),
      '立即发布', async function() {
        var selected = document.querySelector('input[name="publish-account"]:checked');
        if (!selected) { toast('请选择一个账号', 'error'); return; }
        try {
          var result = await API.publishContent(contentId, parseInt(selected.value));
          toast(result.success ? '发布成功' : '发布失败: ' + result.error, result.success ? 'success' : 'error');
          closeModal(); await renderContentList();
        } catch (e) { toast(e.message, 'error'); }
      });
  }

  async function deleteContent(contentId) {
    if (!confirm('确定删除此内容?')) return;
    try { await API.deleteContent(contentId); toast('已删除', 'success'); await renderContentList(); } catch (e) { toast(e.message, 'error'); }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return {
    render: render,
    switchTab: switchTab,
    showCreateModal: showCreateModal,
    showEditModal: showEditModal,
    showPublishModal: showPublishModal,
    deleteContent: deleteContent,
    uploadMedia: uploadMedia,
    deleteMedia: deleteMedia,
    filterMedia: filterMedia,
    aiGenerate: aiGenerate,
    aiGenHashtags: aiGenHashtags,
    aiRegenerate: aiRegenerate,
    aiSaveContent: aiSaveContent,
    showTemplateModal: showTemplateModal,
    deleteTemplate: deleteTemplate,
  };
})();
