// Backend finance API'siyle konuşan tip-güvenli istemci.
// Tutarlar kesinlik için string olarak taşınır (Decimal -> string).

export type ServiceItemIn = {
  description: string;
  daily_rate: string;
  currency: string;
  days: string;
  vat_rate: string;
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
  vat_rate: string;
  line_total: string;
  vat_amount: string;
};

export type InvoiceResponse = {
  id: string;
  status: string;
  currency: string;
  customer_company: string;
  issue_date: string;
  lines: InvoiceLineOut[];
  total: string;
  vat_total: string;
  gross_total: string;
  gib_number: string | null;
  ettn: string | null;
};

export type CustomerPartyIn = {
  tax_id: string;
  name: string;
  tax_office?: string;
  city?: string;
  district?: string;
  street?: string;
  first_name?: string;
  family_name?: string;
};

export type IssueEInvoiceRequest = {
  customer: CustomerPartyIn;
  customer_alias?: string | null;
};

export type EInvoiceStatusLog = {
  created_at: string;
  type: number;
  message: string;
};

export type EInvoiceStatusResponse = {
  invoice_id: string;
  local_document_id: string;
  status: string;
  status_code: number;
  message: string;
  logs: EInvoiceStatusLog[];
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

async function transition(id: string, action: "approve" | "send"): Promise<InvoiceResponse> {
  const response = await fetch(`/api/finance/invoices/${id}/${action}`, { method: "POST" });
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

export function approveInvoice(id: string): Promise<InvoiceResponse> {
  return transition(id, "approve");
}

export function sendInvoice(id: string): Promise<InvoiceResponse> {
  return transition(id, "send");
}

export async function deleteInvoice(id: string): Promise<void> {
  const response = await fetch(`/api/finance/invoices/${id}`, { method: "DELETE" });
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
}

export async function issueEInvoice(
  id: string,
  request: IssueEInvoiceRequest,
): Promise<InvoiceResponse> {
  const response = await fetch(`/api/finance/invoices/${id}/issue`, {
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

export async function getEInvoiceStatus(id: string): Promise<EInvoiceStatusResponse> {
  const response = await fetch(`/api/finance/invoices/${id}/einvoice-status`);
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
  return (await response.json()) as EInvoiceStatusResponse;
}

export function einvoicePdfUrl(id: string): string {
  return `/api/finance/invoices/${id}/einvoice-pdf`;
}

export async function getInvoiceSource(id: string): Promise<CompileInvoiceRequest> {
  const response = await fetch(`/api/finance/invoices/${id}/source`);
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? "Bu faturanın kaynak girdileri yok (düzenlenemiyor)."
        : `Hata ${response.status}`,
    );
  }
  return (await response.json()) as CompileInvoiceRequest;
}
