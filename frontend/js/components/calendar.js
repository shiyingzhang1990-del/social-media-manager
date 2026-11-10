/**
 * Content calendar - month-grid view of scheduled posts.
 */
const CalendarView = (() => {
  let currentYear, currentMonth;
  let scheduledPosts = [];

  const PLATFORM_COLORS = {
    xiaohongshu: '#ff2442', weibo: '#e6162d', bilibili: '#00a1d6',
    douyin: '#111', wechat: '#07c160',
  };

  async function render() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
      const now = new Date();
      currentYear = now.getFullYear();
      currentMonth = now.getMonth() + 1;

      const queueData = await API.listPublishQueue();
      scheduledPosts = queueData.queue.filter(function(item) {
        return item.type === 'schedule';
      });

      renderCalendar(main);
    } catch (e) {
      main.innerHTML = '<div class="empty-state">加载失败: ' + e.message + '</div>';
    }
  }

  function renderCalendar(main) {
    var firstDay = new Date(currentYear, currentMonth - 1, 1);
    var lastDay = new Date(currentYear, currentMonth, 0);
    var startDow = firstDay.getDay();
    var daysInMonth = lastDay.getDate();

    var monthNames = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];

    // Group posts by day
    var postsByDay = {};
    scheduledPosts.forEach(function(p) {
      var d = new Date(p.scheduled_at);
      if (d.getFullYear() === currentYear && d.getMonth() + 1 === currentMonth) {
        var day = d.getDate();
        if (!postsByDay[day]) postsByDay[day] = [];
        postsByDay[day].push(p);
      }
    });

    var html = '<div class="page-header"><h2>内容日历</h2>';
    html += '<div class="btn-group">';
    html += '<button class="btn btn-sm btn-outline" onclick="CalendarView.prevMonth()">&#9664; 上月</button>';
    html += '<span style="font-size:16px;font-weight:600;margin:0 12px">' + currentYear + '年 ' + monthNames[currentMonth - 1] + '</span>';
    html += '<button class="btn btn-sm btn-outline" onclick="CalendarView.nextMonth()">下月 &#9654;</button>';
    html += '<button class="btn btn-sm btn-primary" onclick="CalendarView.goToday()" style="margin-left:8px">今天</button>';
    html += '</div></div>';

    html += '<div class="calendar-grid">';

    // Day headers
    var dowNames = ['日', '一', '二', '三', '四', '五', '六'];
    dowNames.forEach(function(name) {
      html += '<div class="calendar-cell calendar-header">' + name + '</div>';
    });

    // Empty cells before first day
    for (var i = 0; i < startDow; i++) {
      html += '<div class="calendar-cell calendar-empty"></div>';
    }

    // Day cells
    var today = new Date();
    for (var day = 1; day <= daysInMonth; day++) {
      var isToday = today.getFullYear() === currentYear && today.getMonth() + 1 === currentMonth && today.getDate() === day;
      var cls = 'calendar-cell calendar-day' + (isToday ? ' calendar-today' : '');
      var posts = postsByDay[day] || [];

      html += '<div class="' + cls + '">';
      html += '<div class="calendar-day-num">' + day + '</div>';
      if (posts.length > 0) {
        html += '<div class="calendar-posts">';
        posts.forEach(function(p) {
          html += '<div class="calendar-post-dot" style="background:' + (PLATFORM_COLORS[p.platform] || '#999') + '" title="' + p.platform + ': ' + (p.nickname || '') + ' - ' + new Date(p.scheduled_at).toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'}) + '"></div>';
        });
        html += '</div>';
      }
      html += '</div>';
    }

    html += '</div>';

    // Legend
    html += '<div class="card" style="margin-top:16px"><div class="card-header">图例</div><div class="card-body"><div style="display:flex;gap:16px;flex-wrap:wrap">';
    for (var plat in PLATFORM_COLORS) {
      var platNames = { xiaohongshu: '小红书', weibo: '微博', bilibili: 'B站', douyin: '抖音', wechat: '微信' };
      html += '<div style="display:flex;align-items:center;gap:6px;font-size:13px"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:' + PLATFORM_COLORS[plat] + '"></span> ' + (platNames[plat] || plat) + '</div>';
    }
    html += '</div></div></div>';

    // Upcoming schedules list
    var upcoming = scheduledPosts.filter(function(p) {
      return p.status === 'pending';
    }).sort(function(a, b) { return new Date(a.scheduled_at) - new Date(b.scheduled_at); }).slice(0, 10);

    if (upcoming.length > 0) {
      html += '<div class="card" style="margin-top:16px"><div class="card-header">即将发布</div><div class="card-body"><div class="table-wrapper"><table>';
      html += '<thead><tr><th>时间</th><th>平台</th><th>账号</th><th>内容ID</th><th>状态</th></tr></thead><tbody>';
      html += upcoming.map(function(p) {
        return '<tr><td>' + new Date(p.scheduled_at).toLocaleString('zh-CN') + '</td>' +
          '<td><span class="platform-badge plat-' + p.platform + '">' + p.platform + '</span></td>' +
          '<td>' + escapeHtml(p.nickname || '') + '</td>' +
          '<td>' + p.content_id + '</td>' +
          '<td><span class="badge badge-pending">等待中</span></td></tr>';
      }).join('');
      html += '</tbody></table></div></div></div>';
    }

    main.innerHTML = html;
  }

  function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    var main = document.getElementById('main-content');
    renderCalendar(main);
  }

  function prevMonth() { changeMonth(-1); }
  function nextMonth() { changeMonth(1); }

  function goToday() {
    var now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1;
    var main = document.getElementById('main-content');
    renderCalendar(main);
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  return { render: render, prevMonth: prevMonth, nextMonth: nextMonth, goToday: goToday };
})();
