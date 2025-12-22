import { defineStore } from 'pinia';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const useBookingStore = defineStore('booking', {
  state: () => ({
    courses: [],
    bookings: [],
    loading: false,
    error: null,
  }),
  getters: {
    availableCourses: (state) => state.courses.filter(course => course.availableSlots > 0),
    getCourseById: (state) => (id) => state.courses.find(course => course.id === id),
    getUserBookings: (state) => (userId) => state.bookings.filter(booking => booking.userId === userId),
  },
  actions: {
    async fetchCourses() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_BASE_URL}/api/courses`);
        this.courses = response.data;
      } catch (error) {
        this.error = 'Failed to fetch courses. Please try again later.';
        console.error('Error fetching courses:', error);
      } finally {
        this.loading = false;
      }
    },
    async fetchBookings(userId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_BASE_URL}/api/bookings`, {
          params: { userId }
        });
        this.bookings = response.data;
      } catch (error) {
        this.error = 'Failed to fetch bookings. Please try again later.';
        console.error('Error fetching bookings:', error);
      } finally {
        this.loading = false;
      }
    },
    async createBooking(courseId, userId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.post(`${API_BASE_URL}/api/bookings`, {
          courseId,
          userId
        });
        this.bookings.push(response.data);
        
        // Update course available slots
        const course = this.courses.find(c => c.id === courseId);
        if (course) {
          course.availableSlots -= 1;
        }
        
        return response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create booking. Please try again later.';
        console.error('Error creating booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async cancelBooking(bookingId) {
      this.loading = true;
      this.error = null;
      try {
        await axios.delete(`${API_BASE_URL}/api/bookings/${bookingId}`);
        
        // Remove booking from state
        const bookingIndex = this.bookings.findIndex(b => b.id === bookingId);
        if (bookingIndex !== -1) {
          const booking = this.bookings[bookingIndex];
          this.bookings.splice(bookingIndex, 1);
          
          // Update course available slots
          const course = this.courses.find(c => c.id === booking.courseId);
          if (course) {
            course.availableSlots += 1;
          }
        }
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to cancel booking. Please try again later.';
        console.error('Error canceling booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
    clearError() {
      this.error = null;
    }
  }
});