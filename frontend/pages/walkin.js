import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { listMedicines, createWalkInSale } from "../lib/api";

export default function WalkInPage() {
  const [medicines, setMedicines] = useState([]);
  const [customerName, setCustomerName] = useState("");
  const [items, setItems] = useState([]);
  const [medicineId, setMedicineId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");

  useEffect(() => {
    listMedicines().then((res) => setMedicines(res.data));
  }, []);

  const handleAddItem = (e) => {
    e.preventDefault();
    if (!medicineId) return;
    const medicine = medicines.find((m) => String(m.id) === String(medicineId));
    setItems([...items, { medicine_id: medicineId, quantity: Number(quantity), name: medicine?.name, price: medicine?.unit_price }]);
    setMedicineId("");
    setQuantity(1);
  };

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleSubmitSale = async () => {
    if (items.length === 0) return;
    await createWalkInSale({
      customer_name: customerName,
      items: items.map((i) => ({ medicine_id: i.medicine_id, quantity: i.quantity })),
    });
    setMessage("Walk-in sale recorded.");
    setItems([]);
    setCustomerName("");
  };

  const total = items.reduce((sum, i) => sum + (i.price || 0) * i.quantity, 0);

  return (
    <Layout>
      <h2><i className="bi bi-bag-check" /> Walk-in Sale</h2>

      <div className="card">
        <input className="form-control" placeholder="Customer name (optional)"
          value={customerName} onChange={(e) => setCustomerName(e.target.value)} />

        <form onSubmit={handleAddItem} style={{ display: "flex", gap: 8 }}>
          <select className="form-control" value={medicineId} onChange={(e) => setMedicineId(e.target.value)}>
            <option value="">-- select medicine --</option>
            {medicines.map((m) => (
              <option key={m.id} value={m.id}>{m.name} ({m.unit}) - {m.unit_price} - stock {m.stock_quantity}</option>
            ))}
          </select>
          <input type="number" min="1" className="form-control" style={{ maxWidth: 100 }}
            value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          <button type="submit" className="btn"><i className="bi bi-plus-circle" /> Add</button>
        </form>
      </div>

      {items.length > 0 && (
        <div className="card">
          <h3><i className="bi bi-cart" /> Cart</h3>
          {items.map((i, idx) => (
            <div className="list-row" key={idx}>
              <span>{i.name} x{i.quantity} — {(i.price * i.quantity).toFixed(2)}</span>
              <button className="btn btn-sm btn-secondary" onClick={() => handleRemoveItem(idx)}>
                <i className="bi bi-trash" /> Remove
              </button>
            </div>
          ))}
          <h3 style={{ marginTop: 12 }}>Total: {total.toFixed(2)}</h3>
          <button className="btn" onClick={handleSubmitSale}>
            <i className="bi bi-cash-coin" /> Complete Sale
          </button>
        </div>
      )}

      {message && <p className="text-success"><i className="bi bi-info-circle" /> {message}</p>}
    </Layout>
  );
}
