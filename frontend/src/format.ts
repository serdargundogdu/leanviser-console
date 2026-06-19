// TR sunum biçimlendiricileri. Yalnız görüntü içindir; kaynak değer (string/Decimal)
// hiç değişmez — yuvarlama/hesap backend'de yapılır.

export function formatMoney(amount: string, currency: string): string {
  const value = Number(amount);
  if (Number.isNaN(value)) {
    return `${amount} ${currency}`;
  }
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(value);
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) {
    return iso;
  }
  return `${day}.${month}.${year}`;
}

const STATUS_LABELS: Record<string, string> = {
  Draft: "Taslak",
  Approved: "Onaylı",
  Sent: "Gönderildi",
};

const STATUS_COLORS: Record<string, string> = {
  Draft: "#6b7280",
  Approved: "#2563eb",
  Sent: "#059669",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function statusColor(status: string): string {
  return STATUS_COLORS[status] ?? "#6b7280";
}
