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

// Helper to format date "MM/DD"
const formatDate = (dateObj) => {
    const m = dateObj.getMonth() + 1;
    const d = dateObj.getDate();
    return `${m}/${d}`;
};

Page({
    data: {
        currentWeek: 1,
        currentWeekIndex: 0,
        weeksArray: [],
        semester: '2025-2026-1',
        semesterIndex: 0,
        semesterArray: ['2025-2026-1', '2025-2026-2', '2024-2025-1', '2024-2025-2'],
        allCourses: [],
        weekCourses: [],
        rawDays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
        days: [], // [{name:'周一', date:'9/1', isToday:false}, ...]
        currentMonth: new Date().getMonth() + 1,
        loading: true,
        weeksData: [],
        semesterStartDate: null // Date object
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
        const index = parseInt(e.detail.value);
        this.setData({
            currentWeekIndex: index,
            currentWeek: index + 1
        });
        this.updateDatesForWeek(index + 1);
    },

    onSwiperChange(e) {
        const index = e.detail.current;
        if (e.detail.source === 'touch') {
            this.setData({
                currentWeekIndex: index,
                currentWeek: index + 1
            });
            this.updateDatesForWeek(index + 1);
        }
    },

    onSemesterChange(e) {
        const idx = parseInt(e.detail.value);
        const newSemester = this.data.semesterArray[idx];
        this.setData({
            semesterIndex: idx,
            semester: newSemester,
            allCourses: [],
            weeksData: [] // Clear
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
                const serverWeek = res.data.current_week || 1;
                // Prioritize backend start_date
                const backendStartDate = res.data.start_date;

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

                // Calculate Semester Start Date based on backend date or current week
                this.calculateSemesterStart(serverWeek, backendStartDate);

                this.processAllWeeks();
                this.updateDatesForWeek(serverWeek);

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

    processAllWeeks() {
        if (!this.data.allCourses.length) return;

        const allWeeks = [];
        // Loop 1 to 25 weeks
        for (let w = 1; w <= 25; w++) {
            // 1. Filter
            let courses = this.data.allCourses.filter(c => c.weeks_list.includes(w));

            // 2. Sort
            courses.sort((a, b) => {
                if (a.day !== b.day) return a.day - b.day;
                return a.start - b.start;
            });

            // 3. Merge
            const merged = [];
            if (courses.length > 0) {
                let current = { ...courses[0] };
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
                        current.step += next.step;
                    } else {
                        merged.push(current);
                        current = { ...next };
                    }
                }
                merged.push(current);
            }
            allWeeks.push(merged);
        }

        this.setData({ weeksData: allWeeks });
    },

    getCourseColor(name) {
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        const index = Math.abs(hash) % PASTEL_COLORS.length;
        return PASTEL_COLORS[index];
    },

    calculateSemesterStart(currentWeek, backendStartDateStr) {
        if (backendStartDateStr) {
            // Use backend provided start date (YYYY-MM-DD)
            // Note: Replace '-' with '/' for iOS compatibility if needed, but standard usually works
            const parts = backendStartDateStr.split('-');
            // Month is 0-indexed in JS Date
            const start = new Date(parts[0], parts[1] - 1, parts[2]);
            this.setData({ semesterStartDate: start });
            return;
        }

        const today = new Date();
        // Adjust to Monday of current week
        // getDay(): 0(Sun), 1(Mon)... 6(Sat) => We want 1(Mon)...7(Sun)
        let dayOfWeek = today.getDay();
        if (dayOfWeek === 0) dayOfWeek = 7;

        // Current Week Start (Monday)
        const currentWeekStart = new Date(today);
        currentWeekStart.setDate(today.getDate() - (dayOfWeek - 1));

        // Semester Start = Current Week Start - (CurrentWeek - 1) weeks
        const start = new Date(currentWeekStart);
        start.setDate(currentWeekStart.getDate() - (currentWeek - 1) * 7);

        this.setData({ semesterStartDate: start });
    },

    updateDatesForWeek(weekNum) {
        if (!this.data.semesterStartDate) return;

        const start = new Date(this.data.semesterStartDate);
        // Add (weekNum - 1) weeks
        start.setDate(start.getDate() + (weekNum - 1) * 7);

        const newDays = [];
        const todayStr = formatDate(new Date());

        for (let i = 0; i < 7; i++) {
            const d = new Date(start);
            d.setDate(start.getDate() + i);
            const dateStr = formatDate(d);

            newDays.push({
                name: this.data.rawDays[i],
                date: dateStr,
                isToday: dateStr === todayStr
            });
        }

        // Update Month display (use the month of the first day of the week)
        const month = new Date(start).getMonth() + 1;

        this.setData({
            days: newDays,
            currentMonth: month
        });
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
