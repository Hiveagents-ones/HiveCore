import { defineStore } from 'pinia'
import courseApi from '@/api/courses'

export const useCourseStore = defineStore('course', {
  state: () => ({
    courses: [],
    loading: false,
    error: null
  }),
  
  actions: {
    async fetchCourses() {
      this.loading = true
      try {
        this.courses = await courseApi.getAll()
        return this.courses
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async createCourse(courseData) {
      try {
        await courseApi.create(courseData)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    
    async updateCourse(courseId, courseData) {
      try {
        await courseApi.update(courseId, courseData)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    
    async deleteCourse(courseId) {
      try {
        await courseApi.delete(courseId)
      } catch (error) {
        this.error = error.message
        throw error
      }
    },
    
    async enrollCourse(courseId, memberId = 1) {
      try {
        await courseApi.enroll(courseId, memberId)
      } catch (error) {
        this.error = error.message
        throw error
      }
    }
  }
})
