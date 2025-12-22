import { defineStore } from 'pinia';
import courseApi from '../api/courses';

/**
 * 课程状态管理Store
 */
export const useCourseStore = defineStore('course', {
  state: () => ({
    courses: [],
    popularCourses: [],
    currentCourse: null,
    bookings: [],
    coaches: [],
    isLoading: false,
    error: null
  }),

  getters: {
    /**
     * 获取所有课程
     * @returns {Array} 课程列表
     */
    allCourses: (state) => state.courses,
    
    /**
     * 获取热门课程
     * @returns {Array} 热门课程列表
     */
    getPopularCourses: (state) => state.popularCourses,
    
    /**
     * 获取当前选中的课程
     * @returns {Object|null} 当前课程
     */
    selectedCourse: (state) => state.currentCourse,
    
    /**
     * 获取会员预约记录
     * @returns {Array} 预约记录
     */
    memberBookings: (state) => state.bookings,
    
    /**
     * 获取所有教练
     * @returns {Array} 教练列表
     */
    allCoaches: (state) => state.coaches,
    
    /**
     * 获取加载状态
     * @returns {Boolean} 是否正在加载
     */
    loading: (state) => state.isLoading
  },

  actions: {
    /**
     * 获取所有课程
     */
    async fetchCourses() {
      this.isLoading = true;
      try {
        this.courses = await courseApi.getAllCourses();
        this.error = null;
      } catch (err) {
        this.error = err.message;
        console.error('Failed to fetch courses:', err);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 获取热门课程
     */
    async fetchPopularCourses() {
      this.isLoading = true;
      try {
        this.popularCourses = await courseApi.getPopularCourses();
        this.error = null;
      } catch (err) {
        this.error = err.message;
        console.error('Failed to fetch popular courses:', err);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 获取单个课程详情
     * @param {number} courseId 课程ID
     */
    async fetchCourseById(courseId) {
      this.isLoading = true;
      try {
        this.currentCourse = await courseApi.getCourseById(courseId);
        this.error = null;
      } catch (err) {
        this.error = err.message;
        console.error(`Failed to fetch course ${courseId}:`, err);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 预约课程
     * @param {number} courseId 课程ID
     * @param {number} memberId 会员ID
     */
    async bookCourse(courseId, memberId) {
      this.isLoading = true;
      try {
        const result = await courseApi.bookCourse(courseId, memberId);
        this.error = null;
        return result;
      } catch (err) {
        this.error = err.message;
        console.error(`Failed to book course ${courseId}:`, err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 获取会员预约记录
     * @param {number} memberId 会员ID
     */
    async fetchMemberBookings(memberId) {
      this.isLoading = true;
      try {
        this.bookings = await courseApi.getMemberBookings(memberId);
        this.error = null;
      } catch (err) {
        this.error = err.message;
        console.error(`Failed to fetch bookings for member ${memberId}:`, err);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 取消预约
     * @param {number} bookingId 预约ID
     */
    async cancelBooking(bookingId) {
      this.isLoading = true;
      try {
        const result = await courseApi.cancelBooking(bookingId);
        this.error = null;
        return result;
      } catch (err) {
        this.error = err.message;
        console.error(`Failed to cancel booking ${bookingId}:`, err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 获取所有教练
     */
    async fetchAllCoaches() {
      this.isLoading = true;
      try {
        this.coaches = await courseApi.getAllCoaches();
        this.error = null;
      } catch (err) {
        this.error = err.message;
        console.error('Failed to fetch coaches:', err);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 清除当前选中的课程
     */
    clearSelectedCourse() {
      this.currentCourse = null;
    },

    /**
     * 清除错误信息
     */
    clearError() {
      this.error = null;
    }
  }
});