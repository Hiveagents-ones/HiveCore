import axios from "axios";

const API_URL = "http://localhost:8000/api";

export const fetchCourses = async (skip = 0, limit = 100) => {
  const response = await axios.get(`${API_URL}/courses/`, {
    params: { skip, limit },
  });
  return response.data;
};

export const fetchCourse = async (courseId) => {
  const response = await axios.get(`${API_URL}/courses/${courseId}`);
  return response.data;
};

export const createCourse = async (courseData) => {
  const response = await axios.post(`${API_URL}/courses/`, courseData);
  return response.data;
};