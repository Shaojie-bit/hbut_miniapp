const config = require('../../utils/config.js');
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
        currentWeekIndex: 0, // for picker (0-based)
        weeksArray: [], // ["第1周", "第2周", ...]
        semester: '2025-2026-1', // Default
        semesterIndex: 0, // for picker
        semesterArray: ['2025-2026-1', '2025-2026-2', '2024-2025-1', '2024-2025-2'], // Semester options
        allCourses: [],
        weekCourses: [],
        days: [
            { name: '周一' }, { name: '周二' }, { name: '周三' }, { name: '周四' },
            { name: '周五' }, { name: '周六' }, { name: '周日' }
        ],
        currentMonth: new Date().getMonth() + 1,
        loading: true
    },

    onLoad() {
        this.initWeeks();
        this.checkLoginAndFetch();
    },

    onShow() {
        // If we switch back and no data, retry
        if (!this.data.allCourses.length) {
            this.checkLoginAndFetch();
        }
    },

    initWeeks() {
        const arr = [];
        for (let i = 1; i <= 25; i++) {
            arr.push(`第 ${i} 周`);
        }
        this.setData({ weeksArray: arr });
    },

    onWeekChange(e) {
        const week = parseInt(e.detail.value) + 1;
        this.setData({
            currentWeekIndex: e.detail.value,
            currentWeek: week
        });
        this.filterCoursesForWeek(week);
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
        this.fetchTimetable(); // Reload with new semester
    },

    checkLoginAndFetch() {
        const token = wx.getStorageSync('user_token');
        console.log('Schedule Page Token Check:', token);
        if (!token) {
            wx.showToast({ title: '请先登录', icon: 'none' });
            setTimeout(() => {
                wx.redirectTo({ url: '/pages/login/login' });
            }, 1500);
            return;
        }
        this.fetchTimetable();
    },

    async fetchTimetable() {
        wx.showNavigationBarLoading();
        this.setData({ loading: true });

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
                const serverWeek = res.data.current_week || 1; // Default from server

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
                    semester: res.data.semester
                });

                this.filterCoursesForWeek(serverWeek);

            } else if (res.data.code === 401) {
                wx.removeStorageSync('user_token');
                wx.showToast({ title: '登录过期', icon: 'none' });
                setTimeout(() => wx.redirectTo({ url: '/pages/login/login' }), 1000);
            } else {
                wx.showToast({ title: res.data.msg || '获取失败', icon: 'none' });
            }
        } catch (err) {
            console.error(err);
            wx.showToast({ title: '网络请求错误', icon: 'none' });
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
