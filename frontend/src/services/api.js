import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const cargoService = {
  // Submit cargo and tank data
  submitInput: async (cargos, tanks) => {
    const response = await api.post('/input', {
      cargos,
      tanks,
    });
    return response.data;
  },

  // Run optimization
  optimize: async () => {
    const response = await api.post('/optimize');
    return response.data;
  },

  // Get results
  getResults: async () => {
    const response = await api.get('/results');
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
