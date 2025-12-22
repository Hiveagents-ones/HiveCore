import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import axios from 'axios';

export const useCourseStore = defineStore('course', () => {
  // State
  const courses = ref([]);
  const loading = ref(false);
  const error = ref(null);
  const currentPage = ref(1);
  const pageSize = ref(20);
  const totalItems = ref(0);
  const hasMore = ref(true);
  const filters = ref({
    coachId: null,
    category: null,
    dateRange: null
  });

  // Getters
  const filteredCourses = computed(() => {
    let result = [...courses.value];
    
    if (filters.value.coachId) {
      result = result.filter(course => course.coachId === filters.value.coachId);
    }
    
    if (filters.value.category) {
      result = result.filter(course => course.category === filters.value.category);
    }
    
    if (filters.value.dateRange) {
      const [start, end] = filters.value.dateRange;
      result = result.filter(course => {
        const courseDate = new Date(course.date);
        return courseDate >= start && courseDate <= end;
      });
    }
    
    return result;
  });

  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value));

  // Actions
  const fetchCourses = async (page = 1, reset = false) => {
    if (loading.value) return;
    
    loading.value = true;
    error.value = null;
    
    try {
      const params = {
        page,
        limit: pageSize.value,
        ...filters.value
      };
      
      const response = await axios.get('/api/v1/courses', { params });
      
      if (reset) {
        courses.value = response.data.items;
        currentPage.value = 1;
      } else {
        courses.value = [...courses.value, ...response.data.items];
      }
      
      totalItems.value = response.data.total;
      hasMore.value = courses.value.length < totalItems.value;
      currentPage.value = page;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch courses';
      console.error('Error fetching courses:', err);
    } finally {
      loading.value = false;
    }
  };

  const loadMore = async () => {
    if (!hasMore.value || loading.value) return;
    await fetchCourses(currentPage.value + 1, false);
  };

  const resetCourses = async () => {
    courses.value = [];
    currentPage.value = 1;
    hasMore.value = true;
    await fetchCourses(1, true);
  };

  const addCourse = async (courseData) => {
    try {
      const response = await axios.post('/api/v1/courses', courseData);
      courses.value.unshift(response.data);
      totalItems.value += 1;
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to add course';
      throw err;
    }
  };

  const updateCourse = async (id, courseData) => {
    try {
      const response = await axios.put(`/api/v1/courses/${id}`, courseData);
      const index = courses.value.findIndex(course => course.id === id);
      if (index !== -1) {
        courses.value[index] = response.data;
      }
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to update course';
      throw err;
    }
  };

  const deleteCourse = async (id) => {
    try {
      await axios.delete(`/api/v1/courses/${id}`);
      courses.value = courses.value.filter(course => course.id !== id);
      totalItems.value -= 1;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to delete course';
      throw err;
    }
  };

  const setFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters };
  };

  const clearFilters = () => {
    filters.value = {
      coachId: null,
      category: null,
      dateRange: null
    };
  };

  const bookCourse = async (courseId, userId) => {
    try {
      const response = await axios.post(`/api/v1/courses/${courseId}/book`, { userId });
      const course = courses.value.find(c => c.id === courseId);
      if (course) {
        course.bookings = response.data.bookings;
      }
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to book course';
      throw err;
    }
  };

  const cancelBooking = async (courseId, userId) => {
    try {
      const response = await axios.delete(`/api/v1/courses/${courseId}/book`, { data: { userId } });
      const course = courses.value.find(c => c.id === courseId);
      if (course) {
        course.bookings = response.data.bookings;
      }
      return response.data;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to cancel booking';
      throw err;
    }
  };

  return {
    // State
    courses,
    loading,
    error,
    currentPage,
    pageSize,
    totalItems,
    hasMore,
    filters,
    
    // Getters
    filteredCourses,
    totalPages,
    
    // Actions
    fetchCourses,
    loadMore,
    resetCourses,
    addCourse,
    updateCourse,
    deleteCourse,
    setFilters,
    clearFilters,
    bookCourse,
    cancelBooking
  };
});