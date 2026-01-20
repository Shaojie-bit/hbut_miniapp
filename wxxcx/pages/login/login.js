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
        captchaLoading: false,
        needCaptcha: false // Default: Auto-Login mode
    },

    onLoad() {
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
        this.setData({ captchaLoading: true });
        try {
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/captcha`,
                    method: 'GET',
                    success: resolve,
                    fail: reject
                });
            });

            console.log('[Captcha] 响应:', res.data);

            if (res.statusCode === 200 && res.data.code === 200) {
                this.setData({
                    captchaImg: res.data.data.image,
                    tempToken: res.data.data.token,
                    needCaptcha: true
                });
            } else if (res.data.code === 503) {
                wx.showModal({
                    title: '服务暂不可用',
                    content: res.data.msg || '服务器暂时无法使用，请稍后再试',
                    showCancel: false
                });
            } else {
                wx.showToast({ title: res.data.msg || '验证码获取失败', icon: 'none' });
            }
        } catch (err) {
            console.error('[Captcha] 错误:', err);
            wx.showToast({ title: '网络连接失败', icon: 'none' });
        } finally {
            this.setData({ captchaLoading: false });
        }
    },

    // Tap on captcha image to refresh
    onCaptchaTap() {
        this.loadCaptcha();
    },

    async handleLogin() {
        if (!this.data.username || !this.data.password) {
            return wx.showToast({ title: '请输入账号密码', icon: 'none' });
        }

        // If manual mode is active, user must enter captcha
        if (this.data.needCaptcha && !this.data.captcha) {
            return wx.showToast({ title: '请输入验证码', icon: 'none' });
        }

        this.setData({ loading: true });

        // Build payload
        const payload = {
            username: this.data.username,
            password: this.data.password
        };

        // Add captcha if in manual mode
        if (this.data.needCaptcha) {
            payload.token = this.data.tempToken;
            payload.captcha = this.data.captcha;
        }

        try {
            console.log('[Login] 发送登录请求(自动/手动)...');
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/login`,
                    method: 'POST',
                    data: payload,
                    success: resolve,
                    fail: reject
                });
            });

            console.log('[Login] 响应:', res.data);

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
                    wx.switchTab({ url: '/pages/schedule/schedule' });
                }, 1000);

            } else if (res.data.code === 429) {
                // Auto-login failed -> Switch to manual mode
                wx.showToast({ title: '自动识别失败，请手动输入', icon: 'none' });
                this.setData({
                    needCaptcha: true,
                    tempToken: res.data.data.token,
                    captchaImg: res.data.data.image,
                    captcha: ''
                });

            } else {
                // Other errors (Wrong Password, etc)
                wx.showToast({ title: res.data.msg || '登录失败', icon: 'none' });
                // If we were in manual mode, refresh captcha
                if (this.data.needCaptcha) {
                    this.setData({ captcha: '' });
                    this.loadCaptcha();
                }
            }
        } catch (err) {
            console.error('[Login] 错误:', err);
            wx.showToast({ title: '请求超时或网络错误', icon: 'none' });
        } finally {
            this.setData({ loading: false });
        }
    }
});
