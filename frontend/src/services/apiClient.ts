import axios from "axios";
import { msalInstance } from "../main";
import { loginRequest } from "./authConfig";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});

api.interceptors.request.use(async (config) => {
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0) {
    try {
      const result = await msalInstance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
      });
      config.headers.Authorization = `Bearer ${result.accessToken}`;
    } catch {
      await msalInstance.acquireTokenPopup(loginRequest);
    }
  }
  return config;
});

export default api;
