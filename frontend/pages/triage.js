import { useState } from "react";
import Layout from "../components/Layout";
import { submitTriage } from "../lib/api";

export default function TriagePage() {
  const [form, setForm] = useState({
    visit: "", blood_pressure: "", temperature: "", pulse: "", weight: "", height: "", notes: "",
  });
  const [message, setMessage] = useState("");

  const handleChange = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    await submitTriage(form);
    setMessage("Triage recorded. Patient queued for consultation.");
  };

  return (
    <Layout>
      <h2><i className="bi bi-heart-pulse" /> Triage</h2>
      <div className="card">
        <form onSubmit={handleSubmit}>
          <input className="form-control" placeholder="Visit ID" required value={form.visit} onChange={handleChange("visit")} />
          <input className="form-control" placeholder="Blood Pressure (e.g. 120/80)" value={form.blood_pressure} onChange={handleChange("blood_pressure")} />
          <input className="form-control" placeholder="Temperature (°C)" value={form.temperature} onChange={handleChange("temperature")} />
          <input className="form-control" placeholder="Pulse" value={form.pulse} onChange={handleChange("pulse")} />
          <input className="form-control" placeholder="Weight (kg)" value={form.weight} onChange={handleChange("weight")} />
          <input className="form-control" placeholder="Height (cm)" value={form.height} onChange={handleChange("height")} />
          <textarea className="form-control" placeholder="Notes" value={form.notes} onChange={handleChange("notes")} />
          <button type="submit" className="btn">
            <i className="bi bi-check-circle" /> Submit Triage
          </button>
        </form>
      </div>
      {message && <p className="text-success"><i className="bi bi-info-circle" /> {message}</p>}
    </Layout>
  );
}
