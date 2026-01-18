const config = require('../../utils/config.js');
const app = getApp();

Page({
    data: {
        username: '',
        password: '',
        captcha: '',
        captchaImg: '',
        tempToken: '',
        loading: false
    },

    onLoad() {
        this.loadCaptcha();
        // Auto-fill credentials
        const storedUser = wx.getStorageSync('username');
        const storedPwd = wx.getStorageSync('password');
        if (storedUser && storedPwd) {
            this.setData({
                username: storedUser,
                password: storedPwd
            });
        }
    },

    async loadCaptcha() {
        try {
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/captcha`,
                    method: 'GET',
                    success: resolve,
                    fail: reject
                });
            });

            if (res.statusCode === 200 && res.data.code === 200) {
                this.setData({
                    captchaImg: res.data.data.image,
                    tempToken: res.data.data.token
                });
            } else {
                wx.showToast({ title: '验证码获取失败', icon: 'none' });
            }
        } catch (err) {
            console.error(err);
            wx.showToast({ title: '网络连接失败', icon: 'none' });
        }
    },

    async handleLogin() {
        if (!this.data.username || !this.data.password || !this.data.captcha) {
            return wx.showToast({ title: '请填写完整', icon: 'none' });
        }

        this.setData({ loading: true });

        try {
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/login`,
                    method: 'POST',
                    data: {
                        token: this.data.tempToken,
                        username: this.data.username,
                        password: this.data.password,
                        captcha: this.data.captcha
                    },
                    success: resolve,
                    fail: reject
                });
            });

            if (res.statusCode === 200 && res.data.code === 200) {
                // Login Success
                const userToken = res.data.user_token;
                wx.setStorageSync('user_token', userToken);
                wx.setStorageSync('username', this.data.username);
                wx.setStorageSync('password', this.data.password); // Save password for next time
                app.globalData.isLoggedIn = true;
                app.globalData.userToken = userToken;

                wx.showToast({ title: '登录成功', icon: 'success' });

                setTimeout(() => {
                    wx.reLaunch({ url: '/pages/index/index' });
                }, 1000);

            } else {
                wx.showToast({ title: res.data.msg || '登录失败', icon: 'none' });
                this.loadCaptcha(); // Refresh captcha on fail
            }
        } catch (err) {
            console.error(err);
            wx.showToast({ title: '登录请求失败', icon: 'none' });
        } finally {
            this.setData({ loading: false });
        }
    }
});
