import { defineStore } from 'pinia';
import {
  getCourses,
  getCourseDetails,
  bookCourse,
  cancelBooking,
  getBookingCount
} from '../api/courses';

export const useCourseStore = defineStore('course', {
  state: () => ({
    courses: [],
    currentCourse: null,
    bookings: {},
    loading: false,
    error: null,
    concurrentUpdates: new Set()
  }),

  getters: {
    getCourseById: (state) => (id) => {
      return state.courses.find(course => course.id === id);
    },
    getBookingCountById: (state) => (id) => {
      return state.bookings[id] || 0;
    }
  },

  actions: {
    async fetchCourses() {
      this.loading = true;
      try {
        this.courses = await getCourses();
        this.error = null;
      } catch (err) {
        this.error = err.message;
      } finally {
      this.concurrentUpdates.delete(courseId);
      if (courseId) {
        this.concurrentUpdates.delete(courseId);
      }
        this.loading = false;
      }
    },

    async fetchCourseDetails(courseId) {
      this.loading = true;
      try {
        this.currentCourse = await getCourseDetails(courseId);
        this.error = null;
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    async fetchBookingCount(courseId) {
      try {
        const count = await getBookingCount(courseId);
        this.bookings = {
          ...this.bookings,
          [courseId]: count
        };
      } catch (err) {
        console.error('Failed to fetch booking count:', err);
      }
    },

    async bookCourse({ courseId, memberId }) {
      if (this.concurrentUpdates.has(courseId)) {
        throw new Error('该课程正在被其他操作处理中，请稍后再试');
      }
      this.concurrentUpdates.add(courseId);
      this.loading = true;
      try {
        const result = await bookCourse(courseId, memberId);
        await this.fetchBookingCount(courseId);
        this.error = null;
        return result;
      } catch (err) {
        this.error = err.message;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    async cancelBooking(bookingId) {
      const courseId = this.currentCourse?.id;
      if (courseId && this.concurrentUpdates.has(courseId)) {
        throw new Error('该课程正在被其他操作处理中，请稍后再试');
      }
      if (courseId) {
        this.concurrentUpdates.add(courseId);
      }
      this.loading = true;
      try {
        const result = await cancelBooking(bookingId);
        if (this.currentCourse) {
          await this.fetchBookingCount(this.currentCourse.id);
        }
        this.error = null;
        return result;
      } catch (err) {
        this.error = err.message;
        throw err;
      } finally {
        this.loading = false;
      }
    },

    clearCurrentCourse() {
      this.currentCourse = null;
    }
  }
});