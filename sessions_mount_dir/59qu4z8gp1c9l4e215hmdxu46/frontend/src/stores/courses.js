import { defineStore } from 'pinia';
import {
  getCourses,
  getCourseSchedule,
  bookCourse,
  cancelBooking,
  getCourseBookings
} from '@/api/courses';

export const useCoursesStore = defineStore('courses', {
  state: () => ({
    courses: [],
    schedule: [],
    bookings: [],
    isLoading: false,
    error: null,
    lastUpdated: null
,
    bookingStatus: null
,
    bookingError: null
  }),

  getters: {
    upcomingCourses: (state) => {
      const now = new Date();
      return state.schedule.filter(session => {
        return new Date(session.start_time) > now;
      });
    },
    
    pastCourses: (state) => {
      const now = new Date();
      return state.schedule.filter(session => {
        return new Date(session.end_time) < now;
      });
    },
    
    bookedCourses: (state) => {
      return state.schedule.filter(session => {
        return state.bookings.some(
          booking => booking.schedule_id === session.id
        );
      });
    },
    
    hasBookingConflict: (state) => (scheduleId) => {
      const now = new Date();
      const targetSession = state.schedule.find(s => s.id === scheduleId);
      if (!targetSession) return false;
      
      const targetStart = new Date(targetSession.start_time);
      const targetEnd = new Date(targetSession.end_time);
      
      return state.bookings.some(booking => {
        const bookedSession = state.schedule.find(s => s.id === booking.schedule_id);
        if (!bookedSession) return false;
        
        const bookedStart = new Date(bookedSession.start_time);
        const bookedEnd = new Date(bookedSession.end_time);
        
        // 检查时间冲突
        return (
          (targetStart >= bookedStart && targetStart < bookedEnd) ||
          (targetEnd > bookedStart && targetEnd <= bookedEnd) ||
          (targetStart <= bookedStart && targetEnd >= bookedEnd)
        ) && new Date(bookedSession.start_time) > now;
      });
    }
  },

  actions: {
    async fetchCourses() {
      this.isLoading = true;
      this.error = null;
      try {
        this.courses = await getCourses();
        this.lastUpdated = new Date().toISOString();
        return this.courses;
      } catch (error) {
        this.error = error;
        console.error('Failed to fetch courses:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    },


    async fetchSchedule() {
      this.isLoading = true;
      this.error = null;
      try {
        this.schedule = await getCourseSchedule();
        this.lastUpdated = new Date().toISOString();
      } catch (error) {
        this.error = error;
        console.error('Failed to fetch course schedule:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    async fetchBookings() {
    async refreshAll() {
      try {
        await Promise.all([
          this.fetchCourses(),
          this.fetchSchedule(),
          this.fetchBookings()
        ]);
      } catch (error) {
        this.error = error;
        throw error;
      }
    },
      this.isLoading = true;
      this.error = null;
      try {
        this.bookings = await getCourseBookings();
        this.lastUpdated = new Date().toISOString();
      } catch (error) {
        this.error = error;
        console.error('Failed to fetch course bookings:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    async bookCourse(courseId, memberId, scheduleId) {
      this.isLoading = true;
      this.bookingStatus = 'processing';
      this.error = null;
      try {
        const booking = await bookCourse(courseId, memberId, scheduleId);
        await Promise.all([
          this.fetchSchedule(),
          this.fetchBookings()
        ]); // Refresh both schedule and bookings after booking
        this.bookingStatus = 'success';
        return booking;
      } catch (error) {
        this.error = error;
        this.bookingStatus = 'failed';
        this.bookingError = error;
        console.error('Failed to book course:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    async cancelBooking(bookingId, memberId) {
      this.isLoading = true;
      this.error = null;
      try {
        const result = await cancelBooking(bookingId, memberId);
        await Promise.all([
          this.fetchSchedule(),
          this.fetchBookings()
        ]); // Refresh both schedule and bookings after cancellation
        return result;
      } catch (error) {
        this.error = error;
        console.error('Failed to cancel booking:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    }
  }
});