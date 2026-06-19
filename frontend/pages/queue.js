import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Layout from "../components/Layout";
import { getQueue, startConsultation } from "../lib/api";

export default function ConsultationQueuePage() {
  const [queue, setQueue] = useState([]);
  const router = useRouter();

  useEffect(() => {
    getQueue().then((res) => setQueue(res.data));
  }, []);

  const handleStart = async (visitId) => {
    const res = await startConsultation(visitId);
    router.push(`/consultation/${res.data.id}`);
  };

  return (
    <Layout>
      <h2><i className="bi bi-people" /> Consultation Queue</h2>

      <div className="card">
        {queue.length === 0 && <p className="text-muted">No patients waiting.</p>}
        {queue.map((visit) => (
          <div className="list-row" key={visit.id} style={{ alignItems: "flex-start" }}>
            <div>
              <strong>{visit.patient.first_name} {visit.patient.last_name}</strong>
              <div className="text-muted">{visit.consultation_type.name}</div>
              <div className="text-muted">
                BP: {visit.triage?.blood_pressure || "—"} · Temp: {visit.triage?.temperature || "—"} · Pulse: {visit.triage?.pulse || "—"}
              </div>
            </div>
            <button className="btn btn-sm" onClick={() => handleStart(visit.id)}>
              <i className="bi bi-play-circle" /> Start
            </button>
          </div>
        ))}
      </div>
    </Layout>
  );
}
