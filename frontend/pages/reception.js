import { useState } from "react";
import Layout from "../components/Layout";
import {
  searchPatients, registerPatient, createVisit, listConsultationTypes,
} from "../lib/api";

export default function ReceptionPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [newPatient, setNewPatient] = useState({
    first_name: "", last_name: "", phone: "", gender: "M",
  });
  const [consultationTypes, setConsultationTypes] = useState([]);
  const [selectedType, setSelectedType] = useState("");
  const [message, setMessage] = useState("");

  const loadConsultationTypes = async () => {
    const res = await listConsultationTypes();
    setConsultationTypes(res.data);
    if (res.data.length) setSelectedType(res.data[0].id);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    const res = await searchPatients(query);
    setResults(res.data);
    setSearched(true);
    loadConsultationTypes();
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const res = await registerPatient(newPatient);
    setMessage(`Patient ${res.data.first_name} registered.`);
    setResults([res.data]);
    loadConsultationTypes();
  };

  const handleCreateVisit = async (patientId) => {
    if (!selectedType) {
      setMessage("Pick a consultation type first.");
      return;
    }
    await createVisit({ patient_id: patientId, consultation_type_id: selectedType });
    setMessage("Visit created. Patient is ready for triage.");
  };

  return (
    <Layout>
      <h2><i className="bi bi-person-plus" /> Reception</h2>

      <div className="card">
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 8 }}>
          <input
            className="form-control"
            placeholder="Search by name or phone"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn">
            <i className="bi bi-search" /> Search
          </button>
        </form>
      </div>

      {consultationTypes.length > 0 && (
        <div className="card">
          <label><i className="bi bi-clipboard2-pulse" /> Visiting for:</label>
          <select className="form-control" value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
            {consultationTypes.map((ct) => (
              <option key={ct.id} value={ct.id}>{ct.name} - {ct.price}</option>
            ))}
          </select>
        </div>
      )}

      {results.length > 0 && (
        <div className="card">
          <h3><i className="bi bi-list-ul" /> Results</h3>
          {results.map((p) => (
            <div className="list-row" key={p.id}>
              <span><strong>{p.first_name} {p.last_name}</strong> — {p.phone}</span>
              <button className="btn btn-sm" onClick={() => handleCreateVisit(p.id)}>
                <i className="bi bi-plus-circle" /> Create Visit
              </button>
            </div>
          ))}
        </div>
      )}

      {searched && results.length === 0 && (
        <div className="card">
          <p className="text-muted">No patient found. Register a new patient:</p>
          <form onSubmit={handleRegister}>
            <input className="form-control" placeholder="First name" required
              value={newPatient.first_name}
              onChange={(e) => setNewPatient({ ...newPatient, first_name: e.target.value })} />
            <input className="form-control" placeholder="Last name" required
              value={newPatient.last_name}
              onChange={(e) => setNewPatient({ ...newPatient, last_name: e.target.value })} />
            <input className="form-control" placeholder="Phone" required
              value={newPatient.phone}
              onChange={(e) => setNewPatient({ ...newPatient, phone: e.target.value })} />
            <select className="form-control"
              value={newPatient.gender}
              onChange={(e) => setNewPatient({ ...newPatient, gender: e.target.value })}>
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
            <button type="submit" className="btn">
              <i className="bi bi-check-circle" /> Register Patient
            </button>
          </form>
        </div>
      )}

      {message && <p className="text-success"><i className="bi bi-info-circle" /> {message}</p>}
    </Layout>
  );
}
