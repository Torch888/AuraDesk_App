const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || process.env.AURADESK_CLOUD_PORT || 8787);
const DATA_DIR = process.env.AURADESK_CLOUD_DATA_DIR || path.join(__dirname, 'cloud-data');
const DATA_FILE = path.join(DATA_DIR, 'store.json');
const DEFAULT_TOKEN = process.env.AURADESK_CLOUD_TOKEN || 'auradesk-demo-token';

let store = {
  devices: {},
  reminders: [],
  capturedNotifications: [],
  events: []
};

const clients = new Set();

function loadStore() {
  try {
    if (fs.existsSync(DATA_FILE)) {
      store = { ...store, ...JSON.parse(fs.readFileSync(DATA_FILE, 'utf8')) };
    }
  } catch (error) {
    console.warn('读取云端数据失败：', error.message);
  }
}

function saveStore() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(DATA_FILE, JSON.stringify(store, null, 2));
}

function sendJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-auradesk-token, x-auradesk-device-id',
    'Cache-Control': 'no-store'
  });
  res.end(body);
}

function readBody(req) {
  return new Promise(resolve => {
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 1024 * 1024) req.destroy();
    });
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); }
      catch { resolve({}); }
    });
  });
}

function getToken(req, urlObj) {
  const auth = req.headers.authorization || '';
  if (auth.toLowerCase().startsWith('bearer ')) return auth.slice(7).trim();
  return req.headers['x-auradesk-token'] || urlObj.searchParams.get('token') || '';
}

function isAuthorized(req, urlObj) {
  return String(getToken(req, urlObj)) === String(DEFAULT_TOKEN);
}

function normalizeReminder(input = {}) {
  const now = new Date().toISOString();
  return {
    id: input.id || crypto.randomUUID(),
    title: String(input.title || '新的提醒').trim().slice(0, 80) || '新的提醒',
    time: String(input.time || '').trim().slice(0, 40),
    type: String(input.type || '普通').trim().slice(0, 20),
    note: String(input.note || '').trim().slice(0, 500),
    done: Boolean(input.done),
    source: String(input.source || 'cloud').trim().slice(0, 40),
    createdAt: input.createdAt || now,
    updatedAt: now
  };
}

function recordEvent(type, payload = {}) {
  const event = {
    id: crypto.randomUUID(),
    type,
    payload,
    createdAt: new Date().toISOString()
  };
  store.events.unshift(event);
  store.events = store.events.slice(0, 500);
  saveStore();
  broadcast(event);
  return event;
}

function broadcast(event) {
  const message = `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
  for (const res of [...clients]) {
    try { res.write(message); }
    catch { clients.delete(res); }
  }
}

function startSse(req, res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-store, no-transform',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*'
  });
  res.write(': AuraDesk cloud events connected\n\n');
  clients.add(res);
  req.on('close', () => clients.delete(res));
}

async function handleRequest(req, res) {
  const host = req.headers.host || `127.0.0.1:${PORT}`;
  const urlObj = new URL(req.url, `http://${host}`);
  const pathname = decodeURIComponent(urlObj.pathname);

  if (req.method === 'OPTIONS') return sendJson(res, 200, { ok: true });
  if (pathname === '/health') return sendJson(res, 200, { ok: true, app: 'AuraDesk Cloud', port: PORT });

  if (!pathname.startsWith('/api/')) return sendJson(res, 404, { ok: false, message: 'Not found' });
  if (!isAuthorized(req, urlObj)) return sendJson(res, 401, { ok: false, message: '云端 token 不正确' });

  if (req.method === 'GET' && pathname === '/api/events') return startSse(req, res);

  if (req.method === 'POST' && pathname === '/api/devices/register') {
    const body = await readBody(req);
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || crypto.randomUUID()).slice(0, 80);
    store.devices[deviceId] = {
      deviceId,
      name: String(body.name || 'AuraDesk 设备').slice(0, 80),
      platform: String(body.platform || 'unknown').slice(0, 40),
      lastSeenAt: new Date().toISOString()
    };
    saveStore();
    const event = recordEvent('device.registered', store.devices[deviceId]);
    return sendJson(res, 200, { ok: true, device: store.devices[deviceId], event });
  }

  if (req.method === 'GET' && pathname === '/api/reminders') {
    return sendJson(res, 200, { ok: true, reminders: store.reminders });
  }

  if (req.method === 'POST' && pathname === '/api/reminders') {
    const body = await readBody(req);
    const reminder = normalizeReminder(body);
    const existingIndex = store.reminders.findIndex(item => item.id === reminder.id);
    if (existingIndex >= 0) store.reminders[existingIndex] = reminder;
    else store.reminders.unshift(reminder);
    saveStore();
    const event = recordEvent(existingIndex >= 0 ? 'reminder.updated' : 'reminder.created', reminder);
    return sendJson(res, existingIndex >= 0 ? 200 : 201, { ok: true, reminder, event });
  }

  const reminderMatch = pathname.match(/^\/api\/reminders\/([^/]+)$/);
  if (reminderMatch) {
    const id = reminderMatch[1];
    const index = store.reminders.findIndex(item => item.id === id);
    if (index < 0) return sendJson(res, 404, { ok: false, message: '提醒不存在' });

    if (req.method === 'PATCH' || req.method === 'PUT') {
      const body = await readBody(req);
      store.reminders[index] = normalizeReminder({ ...store.reminders[index], ...body, id });
      saveStore();
      const event = recordEvent('reminder.updated', store.reminders[index]);
      return sendJson(res, 200, { ok: true, reminder: store.reminders[index], event });
    }

    if (req.method === 'DELETE') {
      const [removed] = store.reminders.splice(index, 1);
      saveStore();
      const event = recordEvent('reminder.deleted', removed);
      return sendJson(res, 200, { ok: true, removed, event });
    }
  }

  if (req.method === 'POST' && pathname === '/api/notifications/capture') {
    const body = await readBody(req);
    const item = {
      id: crypto.randomUUID(),
      deviceId: String(body.deviceId || req.headers['x-auradesk-device-id'] || 'unknown').slice(0, 80),
      appName: String(body.appName || '').slice(0, 80),
      packageName: String(body.packageName || '').slice(0, 120),
      title: String(body.title || '').slice(0, 120),
      text: String(body.text || '').slice(0, 500),
      postTime: body.postTime || Date.now(),
      createdAt: new Date().toISOString()
    };
    store.capturedNotifications.unshift(item);
    store.capturedNotifications = store.capturedNotifications.slice(0, 1000);
    saveStore();
    const event = recordEvent('notification.captured', item);
    return sendJson(res, 201, { ok: true, notification: item, event });
  }

  if (req.method === 'POST' && pathname === '/api/events') {
    const body = await readBody(req);
    const event = recordEvent(String(body.type || 'custom.event').slice(0, 80), body.payload || {});
    return sendJson(res, 201, { ok: true, event });
  }

  // ─── 家庭健康圈 API ───

  // 获取/创建家庭组
  if (pathname === '/api/family') {
    if (req.method === 'GET') {
      const families = store.families || {};
      return sendJson(res, 200, { ok: true, families });
    }
    if (req.method === 'POST') {
      const body = await readBody(req);
      if (!store.families) store.families = {};
      const familyId = body.familyId || crypto.randomUUID().slice(0, 8);
      const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || 'unknown').slice(0, 80);
      if (!store.families[familyId]) {
        store.families[familyId] = {
          id: familyId,
          name: String(body.name || '我的家庭').slice(0, 40),
          members: [],
          createdAt: new Date().toISOString()
        };
      }
      const family = store.families[familyId];
      if (!family.members.find(m => m.deviceId === deviceId)) {
        family.members.push({
          deviceId,
          name: String(body.memberName || `用户-${deviceId.slice(-4)}`).slice(0, 40),
          joinedAt: new Date().toISOString(),
          authorized: false
        });
      }
      saveStore();
      return sendJson(res, 201, { ok: true, family });
    }
  }

  // 授权查看用药状态
  if (req.method === 'POST' && pathname.match(/^\/api\/family\/[^/]+\/authorize$/)) {
    const familyId = pathname.split('/')[3];
    const body = await readBody(req);
    const family = (store.families || {})[familyId];
    if (!family) return sendJson(res, 404, { ok: false, message: '家庭组不存在' });
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || '').slice(0, 80);
    const member = family.members.find(m => m.deviceId === deviceId);
    if (member) member.authorized = Boolean(body.authorized);
    saveStore();
    return sendJson(res, 200, { ok: true, family });
  }

  // 用药打卡
  if (req.method === 'POST' && pathname === '/api/checkin') {
    const body = await readBody(req);
    if (!store.checkins) store.checkins = [];
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || 'unknown').slice(0, 80);
    const today = new Date().toISOString().slice(0, 10);
    const existing = store.checkins.find(c => c.deviceId === deviceId && c.date === today);
    if (existing) return sendJson(res, 200, { ok: true, checkin: existing, message: '今天已打卡' });
    const checkin = {
      id: crypto.randomUUID(),
      deviceId,
      familyId: String(body.familyId || '').slice(0, 20),
      date: today,
      medications: body.medications || [],
      createdAt: new Date().toISOString()
    };
    store.checkins.push(checkin);
    store.checkins = store.checkins.slice(-2000);
    // 计算连续天数
    const userCheckins = store.checkins.filter(c => c.deviceId === deviceId).sort((a, b) => b.date.localeCompare(a.date));
    let streak = 0;
    let d = new Date();
    for (const c of userCheckins) {
      const expected = d.toISOString().slice(0, 10);
      if (c.date === expected) { streak++; d.setDate(d.getDate() - 1); }
      else break;
    }
    checkin.streak = streak;
    saveStore();
    recordEvent('checkin.completed', { deviceId, streak, date: today });
    return sendJson(res, 201, { ok: true, checkin });
  }

  // 获取打卡排行榜
  if (req.method === 'GET' && pathname === '/api/checkin/leaderboard') {
    const familyId = urlObj.searchParams.get('familyId') || '';
    const today = new Date().toISOString().slice(0, 10);
    const checkins = (store.checkins || []);
    const familyMembers = ((store.families || {})[familyId] || {}).members || [];
    const leaderboard = familyMembers.map(m => {
      const memberCheckins = checkins.filter(c => c.deviceId === m.deviceId).sort((a, b) => b.date.localeCompare(a.date));
      let streak = 0;
      let d = new Date();
      for (const c of memberCheckins) {
        const expected = d.toISOString().slice(0, 10);
        if (c.date === expected) { streak++; d.setDate(d.getDate() - 1); }
        else break;
      }
      return {
        deviceId: m.deviceId,
        name: m.name,
        streak,
        todayDone: memberCheckins.some(c => c.date === today),
        authorized: m.authorized
      };
    }).sort((a, b) => b.streak - a.streak);
    // 统计今日全组打卡人数
    const todayCount = leaderboard.filter(m => m.todayDone).length;
    return sendJson(res, 200, { ok: true, leaderboard, todayCount, totalMembers: familyMembers.length });
  }

  // 发送匿名鼓励卡片
  if (req.method === 'POST' && pathname === '/api/encourage') {
    const body = await readBody(req);
    if (!store.encouragements) store.encouragements = [];
    const card = {
      id: crypto.randomUUID(),
      fromDeviceId: String(body.fromDeviceId || 'anonymous').slice(0, 80),
      toDeviceId: String(body.toDeviceId || '').slice(0, 80),
      familyId: String(body.familyId || '').slice(0, 20),
      cardType: String(body.cardType || 'warm').slice(0, 20),
      message: String(body.message || '加油，你很棒！').slice(0, 200),
      createdAt: new Date().toISOString()
    };
    store.encouragements.push(card);
    store.encouragements = store.encouragements.slice(-500);
    saveStore();
    recordEvent('encourage.sent', { cardId: card.id, toDeviceId: card.toDeviceId });
    return sendJson(res, 201, { ok: true, card });
  }

  // 获取收到的鼓励卡片
  if (req.method === 'GET' && pathname === '/api/encourage') {
    const deviceId = urlObj.searchParams.get('deviceId') || req.headers['x-auradesk-device-id'] || '';
    const cards = (store.encouragements || []).filter(c => c.toDeviceId === deviceId);
    return sendJson(res, 200, { ok: true, cards });
  }

  // 获取群组今日用药状态（小精灵播报用）
  if (req.method === 'GET' && pathname === '/api/health-broadcast') {
    const familyId = urlObj.searchParams.get('familyId') || '';
    const today = new Date().toISOString().slice(0, 10);
    const family = (store.families || {})[familyId];
    if (!family) return sendJson(res, 200, { ok: true, message: '加入家庭组后可查看' });
    const todayDone = (store.checkins || []).filter(c => c.date === today && family.members.some(m => m.deviceId === c.deviceId)).length;
    const total = family.members.length;
    return sendJson(res, 200, { ok: true, todayDone, total, message: `你的病友群里已经有 ${todayDone} 个人完成了今天的用药，加油！` });
  }

  // ─── 交友广场 API ───

  // 保存/更新个人资料
  if (pathname === '/api/social/profile') {
    if (req.method === 'POST') {
      const body = await readBody(req);
      if (!store.socialProfiles) store.socialProfiles = {};
      const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || '').slice(0, 80);
      store.socialProfiles[deviceId] = {
        deviceId,
        nickname: String(body.nickname || '匿名用户').slice(0, 16),
        avatar: String(body.avatar || '🐻').slice(0, 4),
        bio: String(body.bio || '').slice(0, 50),
        updatedAt: new Date().toISOString()
      };
      saveStore();
      return sendJson(res, 200, { ok: true, profile: store.socialProfiles[deviceId] });
    }
  }

  // 广场匿名消息
  if (pathname === '/api/social/nearby') {
    if (req.method === 'GET') {
      const msgs = (store.nearbyMessages || []).slice(0, 50);
      return sendJson(res, 200, { ok: true, messages: msgs });
    }
    if (req.method === 'POST') {
      const body = await readBody(req);
      if (!store.nearbyMessages) store.nearbyMessages = [];
      const msg = {
        id: crypto.randomUUID(),
        deviceId: String(body.deviceId || 'anon').slice(0, 80),
        nickname: String(body.nickname || '匿名').slice(0, 16),
        avatar: String(body.avatar || '🐻').slice(0, 4),
        message: String(body.message || '').slice(0, 120),
        createdAt: new Date().toISOString()
      };
      store.nearbyMessages.unshift(msg);
      store.nearbyMessages = store.nearbyMessages.slice(0, 200);
      saveStore();
      return sendJson(res, 201, { ok: true, message: msg });
    }
  }

  // 碰一碰 - 加入
  if (req.method === 'POST' && pathname === '/api/social/bump/join') {
    const body = await readBody(req);
    if (!store.bumpPool) store.bumpPool = {};
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || '').slice(0, 80);
    store.bumpPool[deviceId] = {
      deviceId,
      nickname: String(body.nickname || '匿名').slice(0, 16),
      avatar: String(body.avatar || '🐻').slice(0, 4),
      joinedAt: new Date().toISOString()
    };
    saveStore();
    return sendJson(res, 200, { ok: true, message: '已加入碰一碰，等待其他人...' });
  }

  // 碰一碰 - 离开
  if (req.method === 'POST' && pathname === '/api/social/bump/leave') {
    const body = await readBody(req);
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || '').slice(0, 80);
    if (store.bumpPool) delete store.bumpPool[deviceId];
    saveStore();
    return sendJson(res, 200, { ok: true });
  }

  // 碰一碰 - 查询状态
  if (req.method === 'GET' && pathname === '/api/social/bump/status') {
    const deviceId = urlObj.searchParams.get('deviceId') || req.headers['x-auradesk-device-id'] || '';
    const pool = store.bumpPool || {};
    // 如果池中有2+人（不包括自己），则匹配成功
    const partners = Object.values(pool).filter(p => p.deviceId !== deviceId);
    if (partners.length >= 1) {
      // 匹配成功，清除池中所有人
      const matched = [...partners];
      store.bumpPool = {};
      saveStore();
      return sendJson(res, 200, { ok: true, matched: true, partners: matched });
    }
    return sendJson(res, 200, { ok: true, matched: false, partners: [] });
  }

  // 晾晒圈 - 发布/获取帖子
  if (pathname === '/api/social/feed') {
    if (req.method === 'GET') {
      return sendJson(res, 200, { ok: true, posts: (store.feedPosts || []).slice(0, 50) });
    }
    if (req.method === 'POST') {
      const body = await readBody(req);
      if (!store.feedPosts) store.feedPosts = [];
      const post = {
        id: crypto.randomUUID(),
        deviceId: String(body.deviceId || 'anon').slice(0, 80),
        nickname: String(body.nickname || '匿名').slice(0, 16),
        avatar: String(body.avatar || '🐻').slice(0, 4),
        content: String(body.content || '').slice(0, 200),
        likes: 0,
        likedBy: [],
        comments: [],
        createdAt: new Date().toISOString()
      };
      store.feedPosts.unshift(post);
      store.feedPosts = store.feedPosts.slice(0, 200);
      saveStore();
      return sendJson(res, 201, { ok: true, post });
    }
  }

  // 晾晒圈 - 点赞
  const likeMatch = pathname.match(/^\/api\/social\/feed\/([^/]+)\/like$/);
  if (likeMatch && req.method === 'POST') {
    const postId = likeMatch[1];
    const post = (store.feedPosts || []).find(p => p.id === postId);
    if (!post) return sendJson(res, 404, { ok: false, message: '帖子不存在' });
    const body = await readBody(req);
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || '').slice(0, 80);
    if (!post.likedBy) post.likedBy = [];
    if (!post.likedBy.includes(deviceId)) {
      post.likedBy.push(deviceId);
      post.likes = (post.likes || 0) + 1;
      saveStore();
    }
    return sendJson(res, 200, { ok: true, likes: post.likes });
  }

  // 晾晒圈 - 评论
  const commentMatch = pathname.match(/^\/api\/social\/feed\/([^/]+)\/comment$/);
  if (commentMatch && req.method === 'POST') {
    const postId = commentMatch[1];
    const post = (store.feedPosts || []).find(p => p.id === postId);
    if (!post) return sendJson(res, 404, { ok: false, message: '帖子不存在' });
    const body = await readBody(req);
    if (!post.comments) post.comments = [];
    post.comments.push({
      id: crypto.randomUUID(),
      deviceId: String(body.deviceId || 'anon').slice(0, 80),
      nickname: String(body.nickname || '匿名').slice(0, 16),
      content: String(body.content || '').slice(0, 100),
      createdAt: new Date().toISOString()
    });
    saveStore();
    return sendJson(res, 201, { ok: true, comment: post.comments[post.comments.length - 1] });
  }

  // 好友 - 获取列表
  if (req.method === 'GET' && pathname === '/api/social/friends') {
    const deviceId = urlObj.searchParams.get('deviceId') || req.headers['x-auradesk-device-id'] || '';
    const friends = (store.friendships || []).filter(f => f.deviceId === deviceId);
    return sendJson(res, 200, { ok: true, friends });
  }

  // 好友 - 添加
  if (req.method === 'POST' && pathname === '/api/social/friends/add') {
    const body = await readBody(req);
    if (!store.friendships) store.friendships = [];
    const deviceId = String(body.deviceId || req.headers['x-auradesk-device-id'] || '').slice(0, 80);
    const friendId = String(body.friendId || '').slice(0, 80);
    // 双向添加
    const exists = store.friendships.some(f => f.deviceId === deviceId && f.friendId === friendId);
    if (!exists) {
      store.friendships.push({
        deviceId,
        friendId,
        friendName: String(body.friendName || '好友').slice(0, 16),
        friendAvatar: String(body.friendAvatar || '🐻').slice(0, 4),
        addedAt: new Date().toISOString()
      });
      store.friendships.push({
        deviceId: friendId,
        friendId: deviceId,
        friendName: String(body.myName || '好友').slice(0, 16),
        friendAvatar: String(body.myAvatar || '🐻').slice(0, 4),
        addedAt: new Date().toISOString()
      });
      saveStore();
    }
    return sendJson(res, 200, { ok: true });
  }

  // 好友消息
  if (pathname === '/api/social/messages') {
    if (req.method === 'GET') {
      const from = urlObj.searchParams.get('from') || '';
      const to = urlObj.searchParams.get('to') || '';
      const msgs = (store.friendMessages || []).filter(m =>
        (m.fromDeviceId === from && m.toDeviceId === to) ||
        (m.fromDeviceId === to && m.toDeviceId === from)
      );
      return sendJson(res, 200, { ok: true, messages: msgs });
    }
    if (req.method === 'POST') {
      const body = await readBody(req);
      if (!store.friendMessages) store.friendMessages = [];
      const msg = {
        id: crypto.randomUUID(),
        fromDeviceId: String(body.fromDeviceId || '').slice(0, 80),
        fromName: String(body.fromName || '').slice(0, 16),
        toDeviceId: String(body.toDeviceId || '').slice(0, 80),
        content: String(body.content || '').slice(0, 200),
        createdAt: new Date().toISOString()
      };
      store.friendMessages.push(msg);
      store.friendMessages = store.friendMessages.slice(-1000);
      saveStore();
      return sendJson(res, 201, { ok: true, message: msg });
    }
  }

  return sendJson(res, 404, { ok: false, message: '接口不存在' });
}

loadStore();
http.createServer((req, res) => {
  handleRequest(req, res).catch(error => {
    console.error('AuraDesk Cloud error:', error);
    sendJson(res, 500, { ok: false, message: error.message });
  });
}).listen(PORT, '0.0.0.0', () => {
  console.log(`AuraDesk Cloud 已启动：http://127.0.0.1:${PORT}`);
  console.log(`当前演示 token：${DEFAULT_TOKEN}`);
});
