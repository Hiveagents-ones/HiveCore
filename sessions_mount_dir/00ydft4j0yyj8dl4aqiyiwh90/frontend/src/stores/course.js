import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchCourses, bookCourse, cancelBooking } from '../api/course';

/**
 * Pinia store for managing course-related state
 */
export const useCourseStore = defineStore('course', () => {
  // State
  const courses = ref([]);
  const loading = ref(false);
  const error = ref(null);
  const bookedCourses = ref([]);

  // Actions
  const loadCourses = async () => {
    try {
      loading.value = true;
      error.value = null;
      const response = await fetchCourses();
      courses.value = response.data;
    } catch (err) {
      error.value = err.message || 'Failed to load courses';
    } finally {
      loading.value = false;
    }
  };

  const bookCourseById = async (courseId) => {
    try {
      loading.value = true;
      error.value = null;
      const response = await bookCourse(courseId);
      bookedCourses.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.message || 'Failed to book course';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const cancelBookedCourse = async (bookingId) => {
    try {
      loading.value = true;
      error.value = null;
      await cancelBooking(bookingId);
      bookedCourses.value = bookedCourses.value.filter(
        (booking) => booking.id !== bookingId
      );
    } catch (err) {
      error.value = err.message || 'Failed to cancel booking';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  // Getters
  const groupClasses = () => {
    return courses.value.filter((course) => course.type === 'group');
  };

  const privateClasses = () => {
    return courses.value.filter((course) => course.type === 'private');
  };

  const isCourseBooked = (courseId) => {
    return bookedCourses.value.some(
      (booking) => booking.course_id === courseId
    );
  };

  return {
    // State
    courses,
    loading,
    error,
    bookedCourses,

    // Actions
    loadCourses,
    bookCourseById,
    cancelBookedCourse,

    // Getters
    groupClasses,
    privateClasses,
    isCourseBooked,
  };
});