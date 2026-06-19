import { useState } from "react";
import Layout from "../components/Layout";
import { getConsultation, recordPayment, dispensePrescription } from "../lib/api";

export default function BillingPage() {
  const [visitId, setVisitId] = useState("");
  const [consultationId, setConsultationId] = useState("");
  const [consultation, setConsultation] = useState(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("CASH");
  const [message, setMessage] = useState("");

  const loadBill = async (e) => {
    e.preventDefault();
    const res = await getConsultation(consultationId);
    setConsultation(res.data);
    setVisitId(res.data.visit);
    setAmount(res.data.grand_total);
  };

  const handlePay = async (e) => {
    e.preventDefault();
    await recordPayment({ visit: visitId, amount, method });
    setMessage("Payment recorded.");
  };

  const handleDispense = async (prescriptionId) => {
    await dispensePrescription(prescriptionId);
    const res = await getConsultation(consultationId);
    setConsultation(res.data);
  };

  return (
    <Layout>
      <h2><i className="bi bi-receipt" /> Billing & Dispensing</h2>

      <div className="card">
        <form onSubmit={loadBill} style={{ display: "flex", gap: 8 }}>
          <input className="form-control" placeholder="Consultation ID" value={consultationId}
            onChange={(e) => setConsultationId(e.target.value)} />
          <button type="submit" className="btn"><i className="bi bi-search" /> Load Bill</button>
        </form>
      </div>

      {consultation && (
        <div className="card">
          <h3><i className="bi bi-file-earmark-text" /> Charges</h3>
          <div className="list-row">
            <span>Consultation fee ({consultation.visit_consultation_type})</span>
            <span>{consultation.consultation_fee}</span>
          </div>
          {consultation.consultation_notes.map((n) => (
            <div className="list-row" key={n.id}>
              <span>{n.title}</span>
              <span>{n.amount}</span>
            </div>
          ))}

          <h4 className="text-muted" style={{ marginTop: 16 }}><i className="bi bi-capsule" /> Medicines</h4>
          {consultation.prescriptions.map((p) => (
            <div className="list-row" key={p.id}>
              <span>{p.medicine.name} x{p.quantity} — {p.subtotal}</span>
              {p.dispensed ? (
                <span className="text-success"><i className="bi bi-check-circle" /> Dispensed</span>
              ) : (
                <button className="btn btn-sm" onClick={() => handleDispense(p.id)}>
                  <i className="bi bi-box-seam" /> Dispense
                </button>
              )}
            </div>
          ))}

          <h3 style={{ marginTop: 16 }}>Grand Total: {consultation.grand_total}</h3>

          <form onSubmit={handlePay} style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input type="number" className="form-control" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <select className="form-control" value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="CASH">Cash</option>
              <option value="MPESA">M-Pesa</option>
              <option value="CARD">Card</option>
              <option value="INSURANCE">Insurance</option>
            </select>
            <button type="submit" className="btn"><i className="bi bi-cash-coin" /> Record Payment</button>
          </form>
        </div>
      )}

      {message && <p className="text-success"><i className="bi bi-info-circle" /> {message}</p>}
    </Layout>
  );
}
