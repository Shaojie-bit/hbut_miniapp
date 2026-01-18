// app.js
App({
  onLaunch() {
    // Exhibit the logs
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)

    // Check if user is logged in
    const token = wx.getStorageSync('user_token')
    if (token) {
      this.globalData.userToken = token
      this.globalData.isLoggedIn = true
    }
  },
  globalData: {
    userInfo: null,
    userToken: null,
    isLoggedIn: false
  }
})
