import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default {
  async getAll() {
    const response = await axios.get(`${API_BASE_URL}/api/v1/courses/`)
    return response.data
  },
  
  async create(courseData) {
    const response = await axios.post(`${API_BASE_URL}/api/v1/courses/`, courseData)
    return response.data
  },
  
  async update(courseId, courseData) {
    const response = await axios.put(`${API_BASE_URL}/api/v1/courses/${courseId}`, courseData)
    return response.data
  },
  
  async delete(courseId) {
    await axios.delete(`${API_BASE_URL}/api/v1/courses/${courseId}`)
  },
  
  async enroll(courseId, memberId) {
    const response = await axios.post(`${API_BASE_URL}/api/v1/courses/${courseId}/enroll`, {
      member_id: memberId
    })
    return response.data
  }
}
