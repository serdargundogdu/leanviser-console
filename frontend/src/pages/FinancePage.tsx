import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import {
  approveInvoice,
  compileInvoice,
  listInvoices,
  sendInvoice,
  type InvoiceResponse,
} from "../api";
import { formatDate, formatMoney, statusColor, statusLabel } from "../format";

const CURRENCIES = ["EUR", "USD", "TRY"];
const EXPENSE_TYPES = ["Fuel", "Meal", "Parking", "Toll", "FlightTicket", "Other"];
const VAT_RATES = ["0.00", "0.01", "0.10", "0.20"];

const field: CSSProperties = { display: "flex", gap: 12, alignItems: "center", marginBottom: 8 };
const labelText: CSSProperties = { minWidth: 130, color: "#374151" };
const control: CSSProperties = { padding: "4px 6px", flex: 1, maxWidth: 280 };
const leftCell: CSSProperties = { textAlign: "left", padding: "6px 8px", borderBottom: "1px solid #eee" };
const rightCell: CSSProperties = { textAlign: "right", padding: "6px 8px", borderBottom: "1px solid #eee" };

function StatusBadge({ status }: { status: string }) {
  return <span style={{ color: statusColor(status), fontWeight: 600 }}>{statusLabel(status)}</span>;
}

export default function FinancePage() {
  const [customer, setCustomer] = useState("ACME");
  const [issueDate, setIssueDate] = useState("2026-06-19");
  const [svcDesc, setSvcDesc] = useState("Danışmanlık hizmet bedeli");
  const [dailyRate, setDailyRate] = useState("750.00");
  const [svcCurrency, setSvcCurrency] = useState("EUR");
  const [days, setDays] = useState("16");
  const [expType, setExpType] = useState("Fuel");
  const [expGross, setExpGross] = useState("120.00");
  const [expVat, setExpVat] = useState("0.20");

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

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInvoice(null);
    try {
      const result = await compileInvoice({
        invoice_id: `INV-${issueDate}-${days}`,
        customer_company: customer,
        issue_date: issueDate,
        currency: "TRY",
        service_items: [{ description: svcDesc, daily_rate: dailyRate, currency: svcCurrency, days }],
        expenses: [{ type: expType, gross: expGross, vat_rate: expVat, currency: "TRY" }],
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

  return (
    <main style={{ maxWidth: 820, margin: "2rem auto", padding: "0 1rem", fontFamily: "system-ui, sans-serif", color: "#111827" }}>
      <h1>LeanViser CONSOLE</h1>
      <h2>Finans — Fatura Derleme</h2>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Fatura</legend>
          <label style={field}>
            <span style={labelText}>Müşteri firma</span>
            <input style={control} value={customer} onChange={(e) => setCustomer(e.target.value)} />
          </label>
          <label style={field}>
            <span style={labelText}>Fatura tarihi</span>
            <input style={control} type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </label>
        </fieldset>

        <fieldset>
          <legend>Hizmet kalemi</legend>
          <label style={field}>
            <span style={labelText}>Açıklama</span>
            <input style={control} value={svcDesc} onChange={(e) => setSvcDesc(e.target.value)} />
          </label>
          <label style={field}>
            <span style={labelText}>Günlük ücret</span>
            <input style={control} value={dailyRate} onChange={(e) => setDailyRate(e.target.value)} />
          </label>
          <label style={field}>
            <span style={labelText}>Para birimi</span>
            <select style={control} value={svcCurrency} onChange={(e) => setSvcCurrency(e.target.value)}>
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <label style={field}>
            <span style={labelText}>Gün sayısı</span>
            <input style={control} value={days} onChange={(e) => setDays(e.target.value)} />
          </label>
        </fieldset>

        <fieldset>
          <legend>Masraf (TRY)</legend>
          <label style={field}>
            <span style={labelText}>Tür</span>
            <select style={control} value={expType} onChange={(e) => setExpType(e.target.value)}>
              {EXPENSE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label style={field}>
            <span style={labelText}>Brüt (KDV dahil)</span>
            <input style={control} value={expGross} onChange={(e) => setExpGross(e.target.value)} />
          </label>
          <label style={field}>
            <span style={labelText}>KDV oranı</span>
            <select style={control} value={expVat} onChange={(e) => setExpVat(e.target.value)}>
              {VAT_RATES.map((rate) => (
                <option key={rate} value={rate}>
                  {rate}
                </option>
              ))}
            </select>
          </label>
        </fieldset>

        <button type="submit" disabled={loading} style={{ padding: "8px 16px", fontWeight: 600 }}>
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
                      <button onClick={() => runTransition(approveInvoice, saved.id)}>Onayla</button>
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
