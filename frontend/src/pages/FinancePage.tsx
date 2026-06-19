import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import {
  approveInvoice,
  compileInvoice,
  deleteInvoice,
  getInvoiceSource,
  listInvoices,
  sendInvoice,
  type InvoiceResponse,
} from "../api";
import { formatDate, formatMoney, statusColor, statusLabel } from "../format";

const CURRENCIES = ["EUR", "USD", "TRY"];
const EXPENSE_TYPES = ["Fuel", "Meal", "Parking", "Toll", "FlightTicket", "Other"];
const VAT_RATES = ["0.00", "0.01", "0.10", "0.20"];

type ServiceRow = { description: string; dailyRate: string; currency: string; days: string };
type ExpenseRow = { type: string; gross: string; vatRate: string };

const field: CSSProperties = { display: "flex", gap: 12, alignItems: "center", marginBottom: 8 };
const labelText: CSSProperties = { minWidth: 110, color: "#374151" };
const rowStyle: CSSProperties = { display: "flex", gap: 8, alignItems: "center", marginBottom: 8, flexWrap: "wrap" };
const addBtn: CSSProperties = { border: "1px dashed #9ca3af", borderRadius: 4, padding: "4px 10px", cursor: "pointer", background: "none", color: "#374151" };
const leftCell: CSSProperties = { textAlign: "left", padding: "6px 8px", borderBottom: "1px solid #eee" };
const rightCell: CSSProperties = { textAlign: "right", padding: "6px 8px", borderBottom: "1px solid #eee" };

function StatusBadge({ status }: { status: string }) {
  return <span style={{ color: statusColor(status), fontWeight: 600 }}>{statusLabel(status)}</span>;
}

export default function FinancePage() {
  const [invoiceId, setInvoiceId] = useState("INV-001");
  const [customer, setCustomer] = useState("ACME");
  const [issueDate, setIssueDate] = useState("2026-06-19");
  const [serviceItems, setServiceItems] = useState<ServiceRow[]>([
    { description: "Danışmanlık hizmet bedeli", dailyRate: "750.00", currency: "EUR", days: "16" },
  ]);
  const [expenses, setExpenses] = useState<ExpenseRow[]>([
    { type: "Fuel", gross: "120.00", vatRate: "0.20" },
  ]);

  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);
  const [invoices, setInvoices] = useState<InvoiceResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function loadInvoices() {
    listInvoices()
      .then(setInvoices)
      .catch(() => {
        // liste yenilenemezse form akışını bozmadan sessiz geç
      });
  }

  useEffect(loadInvoices, []);

  function updateService(index: number, patch: Partial<ServiceRow>) {
    setServiceItems((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }
  function updateExpense(index: number, patch: Partial<ExpenseRow>) {
    setExpenses((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInvoice(null);
    try {
      const result = await compileInvoice({
        invoice_id: invoiceId,
        customer_company: customer,
        issue_date: issueDate,
        currency: "TRY",
        service_items: serviceItems.map((s) => ({
          description: s.description,
          daily_rate: s.dailyRate,
          currency: s.currency,
          days: s.days,
        })),
        expenses: expenses.map((e) => ({
          type: e.type,
          gross: e.gross,
          vat_rate: e.vatRate,
          currency: "TRY",
        })),
      });
      setInvoice(result);
      loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function runTransition(action: (id: string) => Promise<InvoiceResponse>, id: string) {
    setError(null);
    try {
      await action(id);
      loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm(`${id} numaralı fatura silinsin mi?`)) {
      return;
    }
    setError(null);
    try {
      await deleteInvoice(id);
      loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleEdit(id: string) {
    setError(null);
    try {
      const source = await getInvoiceSource(id);
      setInvoiceId(source.invoice_id);
      setCustomer(source.customer_company);
      setIssueDate(source.issue_date);
      setServiceItems(
        source.service_items.map((s) => ({
          description: s.description,
          dailyRate: String(s.daily_rate),
          currency: s.currency,
          days: String(s.days),
        })),
      );
      setExpenses(
        source.expenses.map((e) => ({
          type: e.type,
          gross: String(e.gross),
          vatRate: String(e.vat_rate),
        })),
      );
      setInvoice(null);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <main style={{ maxWidth: 860, margin: "2rem auto", padding: "0 1rem", fontFamily: "system-ui, sans-serif", color: "#111827" }}>
      <h1>LeanViser CONSOLE</h1>
      <h2>Finans — Fatura Derleme</h2>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Fatura</legend>
          <label style={field}>
            <span style={labelText}>Fatura No</span>
            <input value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} />
          </label>
          <label style={field}>
            <span style={labelText}>Müşteri firma</span>
            <input value={customer} onChange={(e) => setCustomer(e.target.value)} />
          </label>
          <label style={field}>
            <span style={labelText}>Fatura tarihi</span>
            <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </label>
        </fieldset>

        <fieldset>
          <legend>Hizmet kalemleri</legend>
          {serviceItems.map((row, index) => (
            <div key={index} style={rowStyle}>
              <input
                placeholder="Açıklama"
                value={row.description}
                onChange={(e) => updateService(index, { description: e.target.value })}
                style={{ flex: 2, minWidth: 160 }}
              />
              <input
                placeholder="Günlük ücret"
                value={row.dailyRate}
                onChange={(e) => updateService(index, { dailyRate: e.target.value })}
                style={{ width: 110 }}
              />
              <select value={row.currency} onChange={(e) => updateService(index, { currency: e.target.value })}>
                {CURRENCIES.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
              <input
                placeholder="Gün"
                value={row.days}
                onChange={(e) => updateService(index, { days: e.target.value })}
                style={{ width: 64 }}
              />
              <button
                type="button"
                aria-label="Hizmet kalemini çıkar"
                onClick={() => setServiceItems((rows) => rows.filter((_, i) => i !== index))}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            style={addBtn}
            onClick={() =>
              setServiceItems((rows) => [...rows, { description: "", dailyRate: "0.00", currency: "EUR", days: "1" }])
            }
          >
            + Hizmet kalemi
          </button>
        </fieldset>

        <fieldset>
          <legend>Masraflar (TRY)</legend>
          {expenses.map((row, index) => (
            <div key={index} style={rowStyle}>
              <select value={row.type} onChange={(e) => updateExpense(index, { type: e.target.value })}>
                {EXPENSE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              <input
                placeholder="Brüt (KDV dahil)"
                value={row.gross}
                onChange={(e) => updateExpense(index, { gross: e.target.value })}
                style={{ width: 140 }}
              />
              <select value={row.vatRate} onChange={(e) => updateExpense(index, { vatRate: e.target.value })}>
                {VAT_RATES.map((rate) => (
                  <option key={rate} value={rate}>
                    KDV {rate}
                  </option>
                ))}
              </select>
              <button
                type="button"
                aria-label="Masrafı çıkar"
                onClick={() => setExpenses((rows) => rows.filter((_, i) => i !== index))}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            style={addBtn}
            onClick={() => setExpenses((rows) => [...rows, { type: "Other", gross: "0.00", vatRate: "0.20" }])}
          >
            + Masraf
          </button>
        </fieldset>

        <button type="submit" disabled={loading} style={{ padding: "8px 16px", fontWeight: 600, marginTop: 8 }}>
          {loading ? "Derleniyor…" : "Fatura Derle"}
        </button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {invoice && (
        <section style={{ marginTop: "1.5rem" }}>
          <p>
            <strong>Fatura {invoice.id}</strong> — {invoice.customer_company} · Durum:{" "}
            <StatusBadge status={invoice.status} /> · {formatDate(invoice.issue_date)}
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={leftCell}>Açıklama</th>
                <th style={rightCell}>Birim</th>
                <th style={rightCell}>Miktar</th>
                <th style={rightCell}>Tutar</th>
              </tr>
            </thead>
            <tbody>
              {invoice.lines.map((line, index) => (
                <tr key={index}>
                  <td style={leftCell}>{line.description}</td>
                  <td style={rightCell}>{formatMoney(line.unit_price, invoice.currency)}</td>
                  <td style={rightCell}>{line.quantity}</td>
                  <td style={rightCell}>{formatMoney(line.line_total, invoice.currency)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td style={leftCell} colSpan={3}>
                  <strong>Toplam</strong>
                </td>
                <td style={rightCell}>
                  <strong>{formatMoney(invoice.total, invoice.currency)}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        </section>
      )}

      {invoices.length > 0 && (
        <section style={{ marginTop: "2rem" }}>
          <h3>Kayıtlı Faturalar ({invoices.length})</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={leftCell}>No</th>
                <th style={leftCell}>Tarih</th>
                <th style={leftCell}>Müşteri</th>
                <th style={leftCell}>Durum</th>
                <th style={rightCell}>Toplam</th>
                <th style={leftCell}>İşlem</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((saved) => (
                <tr key={saved.id}>
                  <td style={leftCell}>{saved.id}</td>
                  <td style={leftCell}>{formatDate(saved.issue_date)}</td>
                  <td style={leftCell}>{saved.customer_company}</td>
                  <td style={leftCell}>
                    <StatusBadge status={saved.status} />
                  </td>
                  <td style={rightCell}>{formatMoney(saved.total, saved.currency)}</td>
                  <td style={leftCell}>
                    {saved.status === "Draft" && (
                      <>
                        <button onClick={() => runTransition(approveInvoice, saved.id)}>Onayla</button>{" "}
                        <button onClick={() => handleEdit(saved.id)}>Düzenle</button>{" "}
                        <button onClick={() => handleDelete(saved.id)}>Sil</button>
                      </>
                    )}
                    {saved.status === "Approved" && (
                      <button onClick={() => runTransition(sendInvoice, saved.id)}>Gönder</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
