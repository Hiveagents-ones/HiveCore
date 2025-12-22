import { defineStore } from 'pinia';
import axios from 'axios';

export const useCourseStore = defineStore('course', {
  state: () => ({
    courses: [],
    loading: false,
    error: null,
  }),
  getters: {
    availableCourses: (state) => {
      return state.courses.filter(course => course.capacity > course.bookedCount);
    },
    getCourseById: (state) => {
      return (courseId) => state.courses.find(course => course.id === courseId);
    },
  },
  actions: {
    async fetchCourses() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/v1/courses');
        this.courses = response.data;
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to fetch courses';
        console.error('Error fetching courses:', error);
      } finally {
        this.loading = false;
      }
    },
    async bookCourse(courseId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.post(`/api/v1/courses/${courseId}/book`);
        const course = this.courses.find(c => c.id === courseId);
        if (course) {
          course.bookedCount = response.data.bookedCount;
        }
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to book course';
        console.error('Error booking course:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async cancelBooking(courseId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.delete(`/api/v1/courses/${courseId}/book`);
        const course = this.courses.find(c => c.id === courseId);
        if (course) {
          course.bookedCount = response.data.bookedCount;
        }
      } catch (error) {
        this.error = error.response?.data?.message || 'Failed to cancel booking';
        console.error('Error canceling booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
  },
});
