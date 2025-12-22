import { defineStore } from 'pinia';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const useBookingStore = defineStore('booking', {
  state: () => ({
    bookings: [],
    currentBooking: null,
    loading: false,
    error: null,
  }),

  getters: {
    getBookingsByCourseId: (state) => (courseId) => {
      return state.bookings.filter(booking => booking.course_id === courseId);
    },
    getBookingsByMemberId: (state) => (memberId) => {
      return state.bookings.filter(booking => booking.member_id === memberId);
    },
    isCourseBookedByMember: (state) => (courseId, memberId) => {
      return state.bookings.some(booking => 
        booking.course_id === courseId && booking.member_id === memberId
      );
    },
  },

  actions: {
    async fetchBookings() {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_BASE_URL}/bookings/`);
        this.bookings = response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch bookings';
        console.error('Error fetching bookings:', error);
      } finally {
        this.loading = false;
      }
    },

    async fetchBookingById(bookingId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_BASE_URL}/bookings/${bookingId}`);
        this.currentBooking = response.data;
        return response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to fetch booking';
        console.error('Error fetching booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async createBooking(bookingData) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.post(`${API_BASE_URL}/bookings/`, bookingData);
        this.bookings.push(response.data);
        this.currentBooking = response.data;
        return response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create booking';
        console.error('Error creating booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async updateBooking(bookingId, bookingData) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.put(`${API_BASE_URL}/bookings/${bookingId}`, bookingData);
        const index = this.bookings.findIndex(booking => booking.id === bookingId);
        if (index !== -1) {
          this.bookings[index] = response.data;
        }
        if (this.currentBooking?.id === bookingId) {
          this.currentBooking = response.data;
        }
        return response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update booking';
        console.error('Error updating booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async deleteBooking(bookingId) {
      this.loading = true;
      this.error = null;
      try {
        await axios.delete(`${API_BASE_URL}/bookings/${bookingId}`);
        this.bookings = this.bookings.filter(booking => booking.id !== bookingId);
        if (this.currentBooking?.id === bookingId) {
          this.currentBooking = null;
        }
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete booking';
        console.error('Error deleting booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async cancelBooking(bookingId) {
      this.loading = true;
      this.error = null;
      try {
        const response = await axios.patch(`${API_BASE_URL}/bookings/${bookingId}/cancel`);
        const index = this.bookings.findIndex(booking => booking.id === bookingId);
        if (index !== -1) {
          this.bookings[index] = response.data;
        }
        if (this.currentBooking?.id === bookingId) {
          this.currentBooking = response.data;
        }
        return response.data;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to cancel booking';
        console.error('Error cancelling booking:', error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    clearError() {
      this.error = null;
    },

    clearCurrentBooking() {
      this.currentBooking = null;
    },
  },
});