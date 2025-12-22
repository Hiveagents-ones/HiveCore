import axios from 'axios';

const API_URL = '/api/v1/members';

export const fetchMembers = async () => {
  try {
    const response = await axios.get(API_URL);
    return response.data;
  } catch (error) {
    throw new Error('Failed to fetch members');
  }
};

export const createMember = async (memberData) => {
  try {
    const response = await axios.post(API_URL, memberData);
    return response.data;
  } catch (error) {
    throw new Error('Failed to create member');
  }
};

export const updateMember = async (id, memberData) => {
  try {
    const response = await axios.put(`${API_URL}/${id}`, memberData);
    return response.data;
  } catch (error) {
    throw new Error('Failed to update member');
  }
};

export const deleteMember = async (id) => {
  try {
    await axios.delete(`${API_URL}/${id}`);
  } catch (error) {
    throw new Error('Failed to delete member');
  }
};