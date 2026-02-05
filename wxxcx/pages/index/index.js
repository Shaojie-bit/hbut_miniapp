const config = require('../../utils/config.js');
const app = getApp();

Page({
  data: {
    semesterGroups: [], // Array of { semesterName, courses: [] }
    rankData: null,
    showRankCard: false,
    loading: true
  },

  onLoad() {
    // 1. Try to load from Cache first (Instant display)
    const cachedGrades = wx.getStorageSync('cached_grades');
    if (cachedGrades) {
      this.processGrades(cachedGrades);
      this.setData({ loading: false });
    }
  },

  onShow() {
    this.checkLoginAndRefresh();
  },

  checkLoginAndRefresh() {
    const token = wx.getStorageSync('user_token');

    if (token) {
      // If we have a token, try to refresh data silently
      this.fetchGrades(true); // true = silent refresh
    } else {
      // No token?
      const cachedGrades = wx.getStorageSync('cached_grades');
      if (!cachedGrades) {
        // No token AND No cache -> Force Login
        wx.redirectTo({ url: '/pages/login/login' });
      } else {
        // No token but have cache -> Offline Mode (Stay here)
        wx.showToast({ title: '离线模式', icon: 'none' });
      }
    }
  },

  async fetchGrades(isSilent = false) {
    // Only show loading if we don't have data yet and it's not silent
    if (!isSilent && this.data.semesterGroups.length === 0) {
      wx.showNavigationBarLoading();
    }

    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${config.BASE_URL}/api/grades`,
          method: 'POST',
          data: { token: wx.getStorageSync('user_token') },
          success: resolve,
          fail: reject
        });
      });

      if (res.statusCode === 200 && res.data.code === 200) {
        const rawGrades = res.data.data;
        // Success! Update Cache
        wx.setStorageSync('cached_grades', rawGrades);
        this.processGrades(rawGrades);

        if (isSilent) console.log("Background refresh success");

      } else if (res.data.code === 401) {
        // Token expired
        console.warn("Token expired");
        wx.removeStorageSync('user_token'); // Remove invalid token

        // If we don't have cache, we MUST redirect. 
        // If we do have cache, we stays in "Offline Mode"
        if (this.data.semesterGroups.length === 0) {
          wx.redirectTo({ url: '/pages/login/login' });
        } else {
          wx.showToast({ title: '登录过期: 显示缓存', icon: 'none' });
        }
      } else {
        if (!isSilent) wx.showToast({ title: '获取成绩失败', icon: 'none' });
      }
    } catch (err) {
      console.error(err);
      if (!isSilent) wx.showToast({ title: '网络错误', icon: 'none' });
    } finally {
      if (!isSilent) wx.hideNavigationBarLoading();
      this.setData({ loading: false });
    }
  },

  processGrades(rawGrades) {
    if (!rawGrades) return;

    // 1. Map raw data to clean format
    const cleanGrades = rawGrades.map(g => ({
      ...g,
      isFail: parseFloat(g.score) < 60 || g.score.includes('不及格')
    }));

    // 2. Group by Semester
    const groups = {};
    cleanGrades.forEach(g => {
      if (!groups[g.semester]) {
        groups[g.semester] = [];
      }
      groups[g.semester].push(g);
    });

    // 3. Convert to Array and Sort Semesters (Newest First)
    const sortedGroups = Object.keys(groups).sort().reverse().map(semName => ({
      semesterName: semName,
      courses: groups[semName]
    }));

    this.setData({ semesterGroups: sortedGroups });
  },

  async toggleRanking() {
    if (this.data.showRankCard) {
      this.setData({ showRankCard: false });
      return;
    }

    if (this.data.rankData) {
      this.setData({ showRankCard: true });
      return;
    }

    const username = wx.getStorageSync('username');
    if (!username) return wx.showToast({ title: '需重新登录', icon: 'none' });

    wx.showLoading({ title: '查询排名中' });
    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${config.BASE_URL}/api/rankings`,
          method: 'POST',
          data: {
            token: wx.getStorageSync('user_token'),
            username: username,
            semester: 'all'
          },
          success: resolve,
          fail: reject
        });
      });

      if (res.statusCode === 200 && res.data.code === 200) {
        this.setData({
          rankData: res.data.data,
          showRankCard: true
        });
      } else {
        wx.showToast({ title: '暂无排名数据', icon: 'none' });
      }
    } catch (err) {
      wx.showToast({ title: '请求失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  }
});
