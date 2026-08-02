import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // 🔥 FIX: Only redirect on 401 if user is NOT already on the login page
    // This prevents the page reload from killing the error toast on failed login
    if (err.response?.status === 401) {
      const isLoginPage = window.location.pathname === '/login' || window.location.pathname === '/';
      const isAuthEndpoint = err.config?.url?.includes('/auth/login') || err.config?.url?.includes('/auth/register');
      
      // Only clear token and redirect if it's a session expiration (not a login failure)
      if (!isLoginPage && !isAuthEndpoint) {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        localStorage.removeItem('role');
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export default api;
