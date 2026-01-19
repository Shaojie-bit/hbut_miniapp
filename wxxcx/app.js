// app.js
const config = require('./utils/config.js');

App({
  onLaunch() {
    // Exhibit the logs
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // Check if user has cached credentials
    const token = wx.getStorageSync('user_token')
    const username = wx.getStorageSync('username')
    const password = wx.getStorageSync('password')

    if (token) {
      this.globalData.userToken = token
      this.globalData.isLoggedIn = true
    }

    // If we have saved credentials, trigger silent auto-login in background
    if (username && password) {
      this.silentAutoLogin(username, password)
    }
  },

  // Silent background login - refreshes token without blocking UI
  async silentAutoLogin(username, password) {
    console.log('[App] Starting silent auto-login...')
    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${config.BASE_URL}/api/login`,
          method: 'POST',
          data: { username, password },
          success: resolve,
          fail: reject
        })
      })

      if (res.statusCode === 200 && res.data.code === 200) {
        const newToken = res.data.user_token
        wx.setStorageSync('user_token', newToken)
        this.globalData.userToken = newToken
        this.globalData.isLoggedIn = true
        this.globalData.tokenRefreshed = true // Flag for pages to know
        console.log('[App] Silent auto-login SUCCESS, new token obtained')
      } else {
        console.log('[App] Silent auto-login failed:', res.data.msg)
        // Don't clear credentials - user can still see cached data
      }
    } catch (err) {
      console.error('[App] Silent auto-login error:', err)
    }
  },

  globalData: {
    userInfo: null,
    userToken: null,
    isLoggedIn: false,
    tokenRefreshed: false
  }
})

