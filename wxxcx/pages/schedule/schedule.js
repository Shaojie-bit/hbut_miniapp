const config = require('../../utils/config.js');
const Auth = require('../../utils/auth.js'); // Import Auth
const app = getApp();

const PASTEL_COLORS = [
    '#A0C4FF', // Blue
    '#FFADAD', // Red
    '#CAFFBF', // Green
    '#FDFFB6', // Yellow
    '#BDB2FF', // Purple
    '#FFC6FF', // Pink
    '#9BF6FF', // Cyan
    '#FFD6A5'  // Orange
];

Page({
    data: {
        currentWeek: 1,
        currentWeekIndex: 0, // for picker and swiper (0-based)
        weeksArray: [], // ["第1周", "第2周", ...]
        semester: '2025-2026-1', // Default
        semesterIndex: 0, // for picker
        semesterArray: ['2025-2026-1', '2025-2026-2', '2024-2025-1', '2024-2025-2'],
        // Semester start dates (Monday of first week)
        semesterStartDates: {
            '2025-2026-1': '2025-09-01',
            '2025-2026-2': '2026-02-23',
            '2024-2025-1': '2024-09-02',
            '2024-2025-2': '2025-02-24'
        },
        allCourses: [],
        weekCourses: [],
        days: [
            { name: '周一', date: '' }, { name: '周二', date: '' }, { name: '周三', date: '' }, { name: '周四', date: '' },
            { name: '周五', date: '' }, { name: '周六', date: '' }, { name: '周日', date: '' }
        ],
        currentMonth: new Date().getMonth() + 1,
        loading: true,
        updateStatus: '', // 'updating', 'success', 'fail'
        updateStatusText: ''
    },

    onLoad() {
        this.initWeeks();
        this.calculateCurrentWeek();

        // 1. Instant rendering from cache
        const cachedTimetable = wx.getStorageSync('cached_timetable');
        if (cachedTimetable) {
            const processed = cachedTimetable.map(c => ({
                ...c,
                color: this.getCourseColor(c.name),
                weeks_list: this.parseWeeks(c.weeks_list)
            }));
            this.setData({
                allCourses: processed,
                loading: false
            });
            this.filterCoursesForWeek(this.data.currentWeek);
        }

        this.updateDaysWithDates(this.data.currentWeek);

        // 2. Silent Login & Update
        this.performSilentUpdate();
    },

    onShow() {
        // Optional: Refresh if cache is empty or it's been a while? 
        // For now, let onLoad handle the main update. 
        // If user manually logged in from Login page, we might want to refresh.
        if (app.globalData.isLoggedIn && !this.data.allCourses.length) {
            this.fetchTimetable();
        }
    },

    async performSilentUpdate() {
        this.setData({ updateStatus: 'updating', updateStatusText: '正在更新课表...' });

        // Try silent login
        const loginRes = await Auth.loginSilently();

        if (loginRes.success) {
            // Login success, fetch data
            await this.fetchTimetable(false); // don't show full screen loading
            this.setData({ updateStatus: 'success', updateStatusText: '已更新最新课表' });
            setTimeout(() => {
                this.setData({ updateStatus: '' });
            }, 2000);
        } else {
            // Login failed (need captcha or wrong password)
            const isOffline = !Auth.hasCredentials();
            if (isOffline) {
                this.setData({ updateStatus: 'fail', updateStatusText: '未登录，仅显示缓存 (点此登录)' });
            } else {
                this.setData({ updateStatus: 'fail', updateStatusText: '更新失败，点此重新登录' });
            }
        }
    },

    handleStatusTap() {
        if (this.data.updateStatus === 'fail') {
            wx.navigateTo({ url: '/pages/login/login' });
        }
    },

    initWeeks() {
        const arr = [];
        for (let i = 1; i <= 25; i++) {
            arr.push(`第 ${i} 周`);
        }
        this.setData({ weeksArray: arr });
    },

    // Calculate current week based on semester start date
    calculateCurrentWeek() {
        const startDateStr = this.data.semesterStartDates[this.data.semester];
        if (!startDateStr) return;

        const startDate = new Date(startDateStr);
        const today = new Date();

        // Calculate the difference in days
        const diffTime = today.getTime() - startDate.getTime();
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        // Calculate week number (1-based)
        let weekNum = Math.floor(diffDays / 7) + 1;

        // Clamp to valid range
        weekNum = Math.max(1, Math.min(25, weekNum));

        this.setData({
            currentWeek: weekNum,
            currentWeekIndex: weekNum - 1
        });
    },

    onWeekChange(e) {
        const week = parseInt(e.detail.value) + 1;
        this.setData({
            currentWeekIndex: e.detail.value,
            currentWeek: week
        });
        this.updateDaysWithDates(week);
        this.filterCoursesForWeek(week);
    },

    // Swiper slide change handler
    onSwiperChange(e) {
        if (e.detail.source === 'touch') {
            const newIndex = e.detail.current;
            const newWeek = newIndex + 1;
            this.setData({
                currentWeekIndex: newIndex,
                currentWeek: newWeek
            });
            this.updateDaysWithDates(newWeek);
            this.filterCoursesForWeek(newWeek);
        }
    },

    // Calculate dates for each day of the week
    updateDaysWithDates(week) {
        const startDateStr = this.data.semesterStartDates[this.data.semester];
        if (!startDateStr) return;

        const startDate = new Date(startDateStr);
        // Offset to Monday of the given week
        const weekOffset = (week - 1) * 7;

        const newDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'].map((name, dayIndex) => {
            const date = new Date(startDate);
            date.setDate(startDate.getDate() + weekOffset + dayIndex);

            const month = date.getMonth() + 1;
            const day = date.getDate();
            const today = new Date();
            const isToday = date.toDateString() === today.toDateString();

            return {
                name,
                date: `${month}/${day}`,
                isToday
            };
        });

        // Update month display (use Monday's month)
        const mondayDate = new Date(startDate);
        mondayDate.setDate(startDate.getDate() + weekOffset);

        this.setData({
            days: newDays,
            currentMonth: mondayDate.getMonth() + 1
        });
    },

    onSemesterChange(e) {
        const idx = parseInt(e.detail.value);
        const newSemester = this.data.semesterArray[idx];
        this.setData({
            semesterIndex: idx,
            semester: newSemester,
            allCourses: [], // Clear old data
            weekCourses: []
        });
        this.calculateCurrentWeek(); // Recalculate current week for new semester
        this.updateDaysWithDates(this.data.currentWeek);
        this.fetchTimetable(); // Reload with new semester
    },

    async fetchTimetable(showLoading = true) {
        if (showLoading) {
            wx.showNavigationBarLoading();
            this.setData({ loading: true });
        }

        try {
            const res = await new Promise((resolve, reject) => {
                wx.request({
                    url: `${config.BASE_URL}/api/timetable`,
                    method: 'POST',
                    data: {
                        token: wx.getStorageSync('user_token'),
                        xnxq: this.data.semester
                    },
                    success: resolve,
                    fail: reject
                });
            });

            if (res.statusCode === 200 && res.data.code === 200) {
                const rawList = res.data.data;
                const serverWeek = res.data.current_week || this.data.currentWeek;

                // Save raw data to cache
                wx.setStorageSync('cached_timetable', rawList);

                // Process data (assign colors)
                const processed = rawList.map(c => ({
                    ...c,
                    color: this.getCourseColor(c.name),
                    weeks_list: this.parseWeeks(c.weeks_list)
                }));

                this.setData({
                    allCourses: processed,
                    currentWeek: serverWeek,
                    currentWeekIndex: serverWeek - 1,
                    semester: res.data.semester || this.data.semester
                });

                // Update dates display after setting current week from server
                this.updateDaysWithDates(serverWeek);
                this.filterCoursesForWeek(serverWeek);
                console.log('[Schedule] Data refreshed from server, current week:', serverWeek);

            } else if (res.data.code === 401) {
                // Token expired
                console.warn('[Schedule] Token expired');
                wx.removeStorageSync('user_token');
                if (showLoading) { // If user manually clicked refresh
                    this.setData({ updateStatus: 'fail', updateStatusText: '会话过期，请重新登录' });
                } else {
                    this.setData({ updateStatus: 'fail', updateStatusText: '更新失败，点此登录' });
                }
            } else {
                if (showLoading) {
                    wx.showToast({ title: res.data.msg || '获取失败', icon: 'none' });
                }
            }
        } catch (err) {
            console.error(err);
            if (showLoading) {
                wx.showToast({ title: '网络请求错误', icon: 'none' });
            }
        } finally {
            wx.hideNavigationBarLoading();
            this.setData({ loading: false });
        }
    },

    parseWeeks(strOrList) {
        // Backend might return "1,2,3" string or already list
        if (Array.isArray(strOrList)) return strOrList;
        if (typeof strOrList === 'string') {
            return strOrList.split(',').map(s => parseInt(s)).filter(n => !isNaN(n));
        }
        return [];
    },

    filterCoursesForWeek(week) {
        if (!this.data.allCourses.length) return;

        // 1. Filter by current week
        let courses = this.data.allCourses.filter(c => c.weeks_list.includes(week));

        // 2. Sort by day and start time
        courses.sort((a, b) => {
            if (a.day !== b.day) return a.day - b.day;
            return a.start - b.start;
        });

        // 3. Merge adjacent courses (same name, room, teacher, day, continuous time)
        const merged = [];
        if (courses.length > 0) {
            let current = { ...courses[0] }; // Clone to avoid mutating original
            for (let i = 1; i < courses.length; i++) {
                const next = courses[i];
                const isSame = (
                    current.day === next.day &&
                    current.name === next.name &&
                    current.teacher === next.teacher &&
                    current.room === next.room
                );
                const isContinuous = (current.start + current.step) === next.start;

                if (isSame && isContinuous) {
                    current.step += next.step; // Extend duration
                } else {
                    merged.push(current);
                    current = { ...next };
                }
            }
            merged.push(current);
        }

        this.setData({ weekCourses: merged });
    },

    getCourseColor(name) {
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        const index = Math.abs(hash) % PASTEL_COLORS.length;
        return PASTEL_COLORS[index];
    },

    showCourseDetail(e) {
        const course = e.currentTarget.dataset.course;
        wx.showModal({
            title: course.name,
            content: `教室: ${course.room}\n老师: ${course.teacher}\n周次: ${course.weeks_desc}\n节次: 周${course.day} ${course.start}-${course.start + course.step - 1}节`,
            showCancel: false,
            confirmText: '知道啦'
        });
    }
});
