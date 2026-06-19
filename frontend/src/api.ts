// Backend finance API'siyle konuşan tip-güvenli istemci.
// Tutarlar kesinlik için string olarak taşınır (Decimal -> string).

export type ServiceItemIn = {
  description: string;
  daily_rate: string;
  currency: string;
  days: string;
};

export type ExpenseIn = {
  type: string;
  gross: string;
  vat_rate: string;
  currency: string;
};

export type CompileInvoiceRequest = {
  invoice_id: string;
  customer_company: string;
  issue_date: string;
  currency: string;
  service_items: ServiceItemIn[];
  expenses: ExpenseIn[];
};

export type InvoiceLineOut = {
  description: string;
  unit_price: string;
  quantity: string;
  line_total: string;
};

export type InvoiceResponse = {
  id: string;
  status: string;
  currency: string;
  customer_company: string;
  issue_date: string;
  lines: InvoiceLineOut[];
  total: string;
};

export async function compileInvoice(
  request: CompileInvoiceRequest,
): Promise<InvoiceResponse> {
  const response = await fetch("/api/finance/invoices", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    let detail = await response.text();
    try {
      const data = JSON.parse(detail);
      if (typeof data?.detail === "string") {
        detail = data.detail;
      }
    } catch {
      // detail düz metin kalsın
    }
    throw new Error(`Hata ${response.status}: ${detail}`);
  }
  return (await response.json()) as InvoiceResponse;
}

export async function listInvoices(): Promise<InvoiceResponse[]> {
  const response = await fetch("/api/finance/invoices");
  if (!response.ok) {
    throw new Error(`Hata ${response.status}`);
  }
  return (await response.json()) as InvoiceResponse[];
}
