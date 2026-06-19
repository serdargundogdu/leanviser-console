import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { compileInvoice, listInvoices, type InvoiceResponse } from "../api";

const CURRENCIES = ["EUR", "USD", "TRY"];
const EXPENSE_TYPES = ["Fuel", "Meal", "Parking", "Toll", "FlightTicket", "Other"];
const VAT_RATES = ["0.00", "0.01", "0.10", "0.20"];

const field: CSSProperties = { display: "block", marginBottom: 8 };
const leftCell: CSSProperties = { textAlign: "left", padding: "4px 8px", borderBottom: "1px solid #eee" };
const rightCell: CSSProperties = { textAlign: "right", padding: "4px 8px", borderBottom: "1px solid #eee" };

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

  return (
    <main style={{ maxWidth: 760, margin: "2rem auto", padding: "0 1rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>LeanViser CONSOLE</h1>
      <h2>Finans — Fatura Derleme</h2>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Fatura</legend>
          <label style={field}>
            Müşteri firma
            <input value={customer} onChange={(e) => setCustomer(e.target.value)} />
          </label>
          <label style={field}>
            Fatura tarihi
            <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </label>
        </fieldset>

        <fieldset>
          <legend>Hizmet kalemi</legend>
          <label style={field}>
            Açıklama
            <input value={svcDesc} onChange={(e) => setSvcDesc(e.target.value)} />
          </label>
          <label style={field}>
            Günlük ücret
            <input value={dailyRate} onChange={(e) => setDailyRate(e.target.value)} />
          </label>
          <label style={field}>
            Para birimi
            <select value={svcCurrency} onChange={(e) => setSvcCurrency(e.target.value)}>
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <label style={field}>
            Gün sayısı
            <input value={days} onChange={(e) => setDays(e.target.value)} />
          </label>
        </fieldset>

        <fieldset>
          <legend>Masraf (TRY)</legend>
          <label style={field}>
            Tür
            <select value={expType} onChange={(e) => setExpType(e.target.value)}>
              {EXPENSE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label style={field}>
            Brüt (KDV dahil)
            <input value={expGross} onChange={(e) => setExpGross(e.target.value)} />
          </label>
          <label style={field}>
            KDV oranı
            <select value={expVat} onChange={(e) => setExpVat(e.target.value)}>
              {VAT_RATES.map((rate) => (
                <option key={rate} value={rate}>
                  {rate}
                </option>
              ))}
            </select>
          </label>
        </fieldset>

        <button type="submit" disabled={loading}>
          {loading ? "Derleniyor…" : "Fatura Derle"}
        </button>
      </form>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {invoice && (
        <section style={{ marginTop: "1.5rem" }}>
          <p>
            <strong>Fatura {invoice.id}</strong> — {invoice.customer_company} · Durum: {invoice.status} ·{" "}
            {invoice.issue_date}
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={leftCell}>Açıklama</th>
                <th style={rightCell}>Birim</th>
                <th style={rightCell}>Miktar</th>
                <th style={rightCell}>Tutar ({invoice.currency})</th>
              </tr>
            </thead>
            <tbody>
              {invoice.lines.map((line, index) => (
                <tr key={index}>
                  <td style={leftCell}>{line.description}</td>
                  <td style={rightCell}>{line.unit_price}</td>
                  <td style={rightCell}>{line.quantity}</td>
                  <td style={rightCell}>{line.line_total}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td style={leftCell} colSpan={3}>
                  <strong>Toplam</strong>
                </td>
                <td style={rightCell}>
                  <strong>
                    {invoice.total} {invoice.currency}
                  </strong>
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
                <th style={leftCell}>Müşteri</th>
                <th style={leftCell}>Durum</th>
                <th style={rightCell}>Toplam</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((saved) => (
                <tr key={saved.id}>
                  <td style={leftCell}>{saved.id}</td>
                  <td style={leftCell}>{saved.customer_company}</td>
                  <td style={leftCell}>{saved.status}</td>
                  <td style={rightCell}>
                    {saved.total} {saved.currency}
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
