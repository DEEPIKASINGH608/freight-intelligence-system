import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const evaluateDecision = async (data) => {
  const response = await axios.post(
    `${API_BASE_URL}/decision/evaluate`,
    data
  );

  return response.data;
};

export const fetchForecast = async (params = {}) => {
  const response = await apiClient.get('/forecast', {
    params,
  });

  return response.data;
};

export const fetchVessels = async () => {
  const response = await apiClient.get('/vessels');

  return response.data;
};

export const fetchRoutes = async () => {
  const response = await apiClient.get('/routes');

  return response.data;
};

export default apiClient;