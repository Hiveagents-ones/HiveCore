import axios from "axios";

const API_URL = "http://localhost:8000/api";

export const fetchBookings = async (skip = 0, limit = 100) => {
  const response = await axios.get(`${API_URL}/bookings/`, {
    params: { skip, limit },
  });
  return response.data;
};

export const fetchBooking = async (bookingId) => {
  const response = await axios.get(`${API_URL}/bookings/${bookingId}`);
  return response.data;
};

export const createBooking = async (bookingData) => {
  const response = await axios.post(`${API_URL}/bookings/`, bookingData);
  return response.data;
};