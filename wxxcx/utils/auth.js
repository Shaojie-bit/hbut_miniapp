const config = require('./config.js');

const Auth = {
    // 检查是否有登录凭证（账号密码）
    hasCredentials() {
        return !!(wx.getStorageSync('username') && wx.getStorageSync('password'));
    },

    // 检查是否有 Token
    hasToken() {
        return !!wx.getStorageSync('user_token');
    },

    // 静默登录 (使用缓存的账号密码)
    // return: { success: boolean, msg: string, needCaptcha: boolean, captchaData: object }
    async loginSilently() {
        const username = wx.getStorageSync('username');
        const password = wx.getStorageSync('password');

        if (!username || !password) {
            return { success: false, msg: '无账号密码缓存', needCaptcha: false };
        }

        try {
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/login`,
                    method: 'POST',
                    data: { username, password }, // 自动模式，不带 captcha/token
                    success: resolve,
                    fail: reject
                });
            });

            console.log('[Auth] Silent Login Response:', res.data);

            if (res.statusCode === 200 && res.data.code === 200) {
                // 登录成功
                const userToken = res.data.user_token;
                wx.setStorageSync('user_token', userToken);
                getApp().globalData.isLoggedIn = true;
                getApp().globalData.userToken = userToken;
                return { success: true, msg: '登录成功' };

            } else if (res.data.code === 429) {
                // 需要验证码 (自动识别失败)
                return {
                    success: false,
                    msg: '需要验证码',
                    needCaptcha: true,
                    captchaData: res.data.data // { token, image }
                };
            } else if (res.data.code === 403) {
                // 限流
                return { success: false, msg: res.data.msg || '请求太频繁' };
            } else {
                // 密码错误或其他
                return { success: false, msg: res.data.msg || '登录失败' };
            }

        } catch (err) {
            console.error('[Auth] Login Error:', err);
            return { success: false, msg: '网络请求失败' };
        }
    },

    // 退出登录
    logout() {
        wx.removeStorageSync('user_token');
        // 可选：是否删除账号密码？通常保留以便下次方便登录
        // wx.removeStorageSync('username');
        // wx.removeStorageSync('password');
        getApp().globalData.isLoggedIn = false;
        getApp().globalData.userToken = '';
    }
};

module.exports = Auth;
