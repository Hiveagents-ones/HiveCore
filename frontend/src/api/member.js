import axios from 'axios';

const API_URL = '/api/members';

export const fetchMemberProfile = async () => {
  const response = await axios.get(`${API_URL}/profile`);
  return response.data;
};

export const updateMemberProfile = async (data) => {
  const response = await axios.put(`${API_URL}/profile`, data);
  return response.data;
};

export const manageMemberCard = async (action, data) => {
  const response = await axios.post(`${API_URL}/cards/${action}`, data);
  return response.data;
};

export const fetchMemberCards = async (memberId) => {
  const response = await axios.get(`${API_URL}/cards/${memberId}`);
  return response.data;
};