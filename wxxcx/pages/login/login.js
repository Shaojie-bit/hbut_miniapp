const config = require('../../utils/config.js');
const app = getApp();

Page({
    data: {
        username: '',
        password: '',
        captcha: '',
        captchaImg: '',
        tempToken: '',
        loading: false,
        needCaptcha: false // Default: Auto-Login mode
    },

    onLoad() {
        // No more initial loadCaptcha()

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
                    tempToken: res.data.data.token,
                    needCaptcha: true
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
        if (!this.data.username || !this.data.password) {
            return wx.showToast({ title: '请输入账号密码', icon: 'none' });
        }

        // If captcha is shown, user must fill it
        if (this.data.needCaptcha && !this.data.captcha) {
            return wx.showToast({ title: '请输入验证码', icon: 'none' });
        }

        this.setData({ loading: true });

        // Payload: If needCaptcha is false, we send only user/pass, backend does OCR
        const payload = {
            username: this.data.username,
            password: this.data.password
        };

        // Add captcha data if needed
        if (this.data.needCaptcha) {
            payload.token = this.data.tempToken;
            payload.captcha = this.data.captcha;
        }

        try {
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/login`,
                    method: 'POST',
                    data: payload,
                    success: resolve,
                    fail: reject
                });
            });

            if (res.statusCode === 200 && res.data.code === 200) {
                // Success
                const userToken = res.data.user_token;
                wx.setStorageSync('user_token', userToken);
                wx.setStorageSync('username', this.data.username);
                wx.setStorageSync('password', this.data.password);
                app.globalData.isLoggedIn = true;
                app.globalData.userToken = userToken;

                wx.showToast({ title: '登录成功', icon: 'success' });
                setTimeout(() => {
                    // Redirect to schedule tab
                    wx.switchTab({ url: '/pages/schedule/schedule' });
                }, 1000);

            } else if (res.data.code === 429 || res.data.data) {
                // Auto-Login Failed (code 429 from backend), Backend requests Manual Input
                this.setData({
                    needCaptcha: true,
                    captchaImg: res.data.data.image,
                    tempToken: res.data.data.token,
                    captcha: '' // Clear input
                });
                wx.showToast({ title: res.data.msg || '请手动输入验证码', icon: 'none', duration: 3000 });

            } else {
                // Other errors (Wrong Password, etc)
                wx.showToast({ title: res.data.msg || '登录失败', icon: 'none' });
                // If we were already in manual mode, refresh captcha
                if (this.data.needCaptcha) this.loadCaptcha();
            }
        } catch (err) {
            console.error(err);
            wx.showToast({ title: '请求超时或错误', icon: 'none' });
        } finally {
            this.setData({ loading: false });
        }
    }
});
