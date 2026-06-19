import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Attach JWT access token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export async function login(username, password, role) {
  const res = await axios.post(`${API_BASE_URL}/auth/login/`, { username, password });
  localStorage.setItem("access_token", res.data.access);
  localStorage.setItem("refresh_token", res.data.refresh);
  // Role drives which sidebar links are shown. The backend enforces the real
  // permission check (IsNurse / IsDoctor) on every request regardless of this.
  localStorage.setItem("role", role);
  localStorage.setItem("username", username);
  return res.data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("role");
  localStorage.removeItem("username");
}

export function getCurrentUser() {
  if (typeof window === "undefined") return { role: null, username: null };
  return {
    role: localStorage.getItem("role"),
    username: localStorage.getItem("username"),
  };
}

export function isAuthenticated() {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

// ---------------- Reception (Nurse) ----------------

export const searchPatients = (query) => api.get(`/patients/?search=${encodeURIComponent(query)}`);
export const registerPatient = (data) => api.post("/patients/", data);
export const createVisit = (data) => api.post("/visits/", data);
export const submitTriage = (data) => api.post("/triage/", data);
export const getVisitPayments = (visitId) => api.get(`/payments/?visit=${visitId}`);
export const recordPayment = (data) => api.post("/payments/", data);
export const dispensePrescription = (prescriptionId) => api.post(`/prescriptions/${prescriptionId}/dispense/`);
export const createWalkInSale = (data) => api.post("/walkin-sales/", data);
export const listMedicines = () => api.get("/medicines/");

// ---------------- Shared lists (Doctor & Nurse) ----------------

export const listPatients = (search = "") => api.get(`/patients/?search=${encodeURIComponent(search)}`);
export const listVisits = (params = "") => api.get(`/visits/${params ? `?${params}` : ""}`);
export const listWalkInSales = () => api.get("/walkin-sales/");
export const getDashboardStats = () => api.get("/dashboard/stats/");

// ---------------- Consultation (Doctor) ----------------

export const getQueue = () => api.get("/visits/queue/");
export const startConsultation = (visitId) => api.post("/consultations/", { visit: visitId });
export const getConsultation = (id) => api.get(`/consultations/${id}/`);
export const addConsultationNote = (consultationId, data) => api.post(`/consultations/${consultationId}/add-note/`, data);
export const prescribeMedicine = (consultationId, data) => api.post(`/consultations/${consultationId}/prescribe/`, data);
export const completeConsultation = (consultationId) => api.post(`/consultations/${consultationId}/complete/`);
export const listICD10 = (query = "") => api.get(`/icd10-codes/?search=${encodeURIComponent(query)}`);
export const listDiagnosisNotes = () => api.get("/diagnosis-notes/");
export const listConsultationTypes = () => api.get("/consultation-types/");

export default api;