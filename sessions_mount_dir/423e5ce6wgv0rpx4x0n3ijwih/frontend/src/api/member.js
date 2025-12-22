// 用户相关API接口
import axios from 'axios';

// API基础URL
const API_BASE_URL = '/api/v1';

/**
 * 用户注册
 * @param {Object} userData - 注册数据
 * @param {string} userData.username - 用户名
 * @param {string} userData.password - 密码
 * @returns {Promise} 注册结果
 */
export const register = async (userData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/users/register`, userData);
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/**
 * 用户登录
 * @param {Object} loginData - 登录数据
 * @param {string} loginData.username - 用户名
 * @param {string} loginData.password - 密码
 * @returns {Promise} 登录结果
 */
export const login = async (loginData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/users/login`, loginData);
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/**
 * 获取用户信息
 * @returns {Promise} 用户信息
 */
export const getUserInfo = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/users/me`);
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/**
 * 更新用户信息
 * @param {Object} userData - 更新的用户数据
 * @returns {Promise} 更新结果
 */
export const updateUserInfo = async (userData) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/users/me`, userData);
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/**
 * 用户登出
 * @returns {Promise} 登出结果
 */
export const logout = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/users/logout`);
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};