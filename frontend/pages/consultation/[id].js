import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Layout from "../../components/Layout";
import {
  getConsultation, listICD10, listDiagnosisNotes, addConsultationNote,
  prescribeMedicine, completeConsultation, listMedicines,
} from "../../lib/api";

export default function ConsultationRoomPage() {
  const router = useRouter();
  const { id } = router.query; // consultation id
  const [consultation, setConsultation] = useState(null);
  const [diagnosisNotes, setDiagnosisNotes] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [icd10Query, setIcd10Query] = useState("");
  const [icd10Results, setIcd10Results] = useState([]);

  const [noteId, setNoteId] = useState("");
  const [customTitle, setCustomTitle] = useState("");
  const [noteAmount, setNoteAmount] = useState("");

  const [medicineId, setMedicineId] = useState("");
  const [quantity, setQuantity] = useState(1);

  const load = async () => {
    if (!id) return;
    const res = await getConsultation(id);
    setConsultation(res.data);
  };

  useEffect(() => {
    if (!id) return;
    load();
    listDiagnosisNotes().then((res) => setDiagnosisNotes(res.data));
    listMedicines().then((res) => setMedicines(res.data));
  }, [id]);

  const handleIcd10Search = async (e) => {
    e.preventDefault();
    const res = await listICD10(icd10Query);
    setIcd10Results(res.data);
  };

  const handleNoteSelect = (val) => {
    setNoteId(val);
    const note = diagnosisNotes.find((n) => String(n.id) === String(val));
    if (note) setNoteAmount(note.default_amount);
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    await addConsultationNote(id, {
      diagnosis_note: noteId || null,
      custom_title: noteId ? "" : customTitle,
      amount: noteAmount,
    });
    setNoteId(""); setCustomTitle(""); setNoteAmount("");
    load();
  };

  const handlePrescribe = async (e) => {
    e.preventDefault();
    await prescribeMedicine(id, { medicine_id: medicineId, quantity });
    setMedicineId(""); setQuantity(1);
    load();
  };

  const handleComplete = async () => {
    await completeConsultation(id);
    router.push("/queue");
  };

  if (!consultation) {
    return (
      <Layout>
        <p className="text-muted">Loading...</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <h2><i className="bi bi-clipboard2-pulse" /> Consultation Room</h2>

      <div className="card">
        <p><strong>Visiting for:</strong> {consultation.visit_consultation_type} (fee: {consultation.consultation_fee})</p>
        {consultation.visit_triage && (
          <p className="text-muted">
            <i className="bi bi-heart-pulse" /> BP {consultation.visit_triage.blood_pressure}, Temp {consultation.visit_triage.temperature},
            Pulse {consultation.visit_triage.pulse}, Weight {consultation.visit_triage.weight}, Height {consultation.visit_triage.height}
            <br />Notes: {consultation.visit_triage.notes}
          </p>
        )}
      </div>

      <div className="card">
        <h3><i className="bi bi-journal-medical" /> ICD-10 Diagnosis</h3>
        <form onSubmit={handleIcd10Search} style={{ display: "flex", gap: 8 }}>
          <input className="form-control" placeholder="Search ICD-10" value={icd10Query} onChange={(e) => setIcd10Query(e.target.value)} />
          <button type="submit" className="btn btn-sm"><i className="bi bi-search" /></button>
        </form>
        {icd10Results.map((code) => (
          <div className="list-row" key={code.id}>
            <span>{code.code} - {code.description}</span>
          </div>
        ))}
        <p className="text-muted" style={{ marginTop: 8 }}>
          <strong>Attached:</strong> {consultation.icd10_codes.map((c) => c.code).join(", ") || "None"}
        </p>
      </div>

      <div className="card">
        <h3><i className="bi bi-card-checklist" /> Diagnosis / Service Notes</h3>
        <form onSubmit={handleAddNote} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select className="form-control" style={{ flex: 1 }} value={noteId} onChange={(e) => handleNoteSelect(e.target.value)}>
            <option value="">-- custom note --</option>
            {diagnosisNotes.map((n) => (
              <option key={n.id} value={n.id}>{n.title} ({n.default_amount})</option>
            ))}
          </select>
          {!noteId && (
            <input className="form-control" style={{ flex: 1 }} placeholder="Custom note title"
              value={customTitle} onChange={(e) => setCustomTitle(e.target.value)} />
          )}
          <input type="number" className="form-control" style={{ maxWidth: 100 }} placeholder="Amount"
            value={noteAmount} onChange={(e) => setNoteAmount(e.target.value)} />
          <button type="submit" className="btn"><i className="bi bi-plus-circle" /> Add</button>
        </form>
        {consultation.consultation_notes.map((n) => (
          <div className="list-row" key={n.id}>
            <span>{n.title}</span><span>{n.amount}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3><i className="bi bi-capsule" /> Prescribe Medicine</h3>
        <form onSubmit={handlePrescribe} style={{ display: "flex", gap: 8 }}>
          <select className="form-control" value={medicineId} onChange={(e) => setMedicineId(e.target.value)}>
            <option value="">-- select medicine --</option>
            {medicines.map((m) => (
              <option key={m.id} value={m.id}>{m.name} ({m.unit}) - stock {m.stock_quantity}</option>
            ))}
          </select>
          <input type="number" min="1" className="form-control" style={{ maxWidth: 80 }}
            value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          <button type="submit" className="btn"><i className="bi bi-plus-circle" /> Add</button>
        </form>
        {consultation.prescriptions.map((p) => (
          <div className="list-row" key={p.id}>
            <span>{p.medicine.name} x{p.quantity}</span><span>{p.subtotal}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Total: {consultation.grand_total}</h3>
        <button className="btn" onClick={handleComplete}>
          <i className="bi bi-check-circle" /> Complete Consultation & Send to Reception
        </button>
      </div>
    </Layout>
  );
}
