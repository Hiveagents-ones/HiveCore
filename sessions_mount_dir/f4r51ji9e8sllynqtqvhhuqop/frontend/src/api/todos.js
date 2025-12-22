import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const todosApi = {
  // 获取所有待办事项
  async getTodos() {
    try {
      const response = await apiClient.get('/api/v1/todos');
      return response.data;
    } catch (error) {
      console.error('Error fetching todos:', error);
      throw error;
    }
  },

  // 创建新的待办事项
  async createTodo(content) {
    try {
      const response = await apiClient.post('/api/v1/todos', { content });
      return response.data;
    } catch (error) {
      console.error('Error creating todo:', error);
      throw error;
    }
  },

  // 更新待办事项
  async updateTodo(id, completed) {
    try {
      const response = await apiClient.put(`/api/v1/todos/${id}`, { completed });
      return response.data;
    } catch (error) {
      console.error('Error updating todo:', error);
      throw error;
    }
  },

  // 删除待办事项
  async deleteTodo(id) {
    try {
      await apiClient.delete(`/api/v1/todos/${id}`);
    } catch (error) {
      console.error('Error deleting todo:', error);
      throw error;
    }
  },
};

export default todosApi;