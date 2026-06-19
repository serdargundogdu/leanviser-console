"""Finance HTTP adapter (driving): fatura derleme uç noktası.

FastAPI router'ı. HTTP DTO'ları (Pydantic) burada yaşar ve application/domain
modellerine map'lenir; çekirdek HTTP bilmez (hexagonal: driving adapter).
Not: Bu dosya Pydantic kullandığı için PEP 563 (future annotations) bilinçli
olarak kullanılmaz — Pydantic alan tiplerini kuruluşta gerçek tip olarak ister.
"""

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.modules.finance.adapters.http.dependencies import (
    get_einvoice_gateway,
    get_einvoice_supplier,
    get_exchange_rate_provider,
    get_invoice_repository,
    get_invoice_series,
)
from app.modules.finance.adapters.uyumsoft_einvoice_gateway import EInvoiceGatewayError
from app.modules.finance.application.compile_invoice import (
    CompileInvoice,
    CompileInvoiceCommand,
    ServiceItem,
)
from app.modules.finance.application.einvoice_gateway import EInvoiceGateway
from app.modules.finance.application.einvoice_models import Party
from app.modules.finance.application.exchange_rate_provider import ExchangeRateProvider
from app.modules.finance.application.invoice_repository import InvoiceRepository
from app.modules.finance.application.issue_einvoice import (
    EInvoiceIssueError,
    IssueEInvoice,
    IssueEInvoiceCommand,
)
from app.modules.finance.domain.expense import Expense, ExpenseType
from app.modules.finance.domain.gib_invoice_number import GibInvoiceNumber
from app.modules.finance.domain.invoice import Invoice, InvoiceStateError, InvoiceStatus
from app.modules.finance.domain.money import Currency, CurrencyMismatchError, Money
from app.modules.finance.domain.vat import VatRate

router = APIRouter(prefix="/finance", tags=["finance"])


class ServiceItemIn(BaseModel):
    """Hizmet kalemi girdisi. Tutarlar kesinlik için string olarak gönderilir."""

    description: str
    daily_rate: Decimal
    currency: str
    days: Decimal
    vat_rate: Decimal = Decimal("0.20")


class ExpenseIn(BaseModel):
    """Masraf girdisi."""

    type: str
    gross: Decimal
    vat_rate: Decimal
    currency: str = "TRY"


class CompileInvoiceRequest(BaseModel):
    """Fatura derleme isteği."""

    invoice_id: str
    customer_company: str
    issue_date: date
    currency: str = "TRY"
    service_items: list[ServiceItemIn] = []
    expenses: list[ExpenseIn] = []


class CustomerPartyIn(BaseModel):
    """e-Fatura alıcı kimliği (domain'de tutulmayan; kesme anında verilir)."""

    tax_id: str  # VKN (10) ya da TCKN (11)
    name: str
    tax_office: str = ""
    city: str = ""
    district: str = ""
    street: str = ""
    first_name: str = ""  # gerçek kişi (TCKN) için
    family_name: str = ""


class IssueEInvoiceRequest(BaseModel):
    """Onaylı faturayı e-Fatura/e-Arşiv olarak kesme isteği."""

    customer: CustomerPartyIn
    customer_alias: str | None = None  # e-Fatura alıcı etiketi (GİB); e-Arşiv'de boş


class EInvoiceStatusLogOut(BaseModel):
    """Durum sorgusu günlük satırı."""

    created_at: datetime
    type: int
    message: str


class EInvoiceStatusResponse(BaseModel):
    """Kesilmiş faturanın entegratör/GİB durumu + günlükleri."""

    invoice_id: str
    local_document_id: str
    status: str
    status_code: int
    message: str
    logs: list[EInvoiceStatusLogOut]


class InvoiceLineOut(BaseModel):
    """Yanıt kalemi (tutarlar string). line_total nettir; vat_amount KDV tutarı."""

    description: str
    unit_price: str
    quantity: str
    vat_rate: str
    line_total: str
    vat_amount: str


class InvoiceResponse(BaseModel):
    """Derlenmiş fatura yanıtı. total nettir; vat_total ve gross_total ayrıca verilir."""

    id: str
    status: str
    currency: str
    customer_company: str
    issue_date: date
    lines: list[InvoiceLineOut]
    total: str
    vat_total: str
    gross_total: str
    gib_number: str | None = None
    ettn: str | None = None


def _currency(code: str) -> Currency:
    try:
        return Currency[code]
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Geçersiz para birimi: {code}") from None


def _expense_type(name: str) -> ExpenseType:
    try:
        return ExpenseType[name]
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Geçersiz masraf türü: {name}") from None


def _to_command(request: CompileInvoiceRequest) -> CompileInvoiceCommand:
    service_items = tuple(
        ServiceItem(
            description=item.description,
            daily_rate=Money(item.daily_rate, _currency(item.currency)),
            days=item.days,
            vat_rate=VatRate(item.vat_rate),
        )
        for item in request.service_items
    )
    expenses = tuple(
        Expense(
            id=f"E-{index}",
            gross=Money(expense.gross, _currency(expense.currency)),
            vat_rate=VatRate(expense.vat_rate),
            type=_expense_type(expense.type),
            date=request.issue_date,
            company=request.customer_company,
        )
        for index, expense in enumerate(request.expenses, start=1)
    )
    return CompileInvoiceCommand(
        invoice_id=request.invoice_id,
        customer_company=request.customer_company,
        issue_date=request.issue_date,
        currency=_currency(request.currency),
        service_items=service_items,
        expenses=expenses,
    )


def _to_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        status=invoice.status.value,
        currency=invoice.currency.code,
        customer_company=invoice.customer_company,
        issue_date=invoice.issue_date,
        lines=[
            InvoiceLineOut(
                description=line.description,
                unit_price=str(line.unit_price.amount),
                quantity=str(line.quantity),
                vat_rate=str(line.vat_rate.rate),
                line_total=str(line.line_total().amount),
                vat_amount=str(line.vat_amount().amount),
            )
            for line in invoice.lines
        ],
        total=str(invoice.total().amount),
        vat_total=str(invoice.vat_total().amount),
        gross_total=str(invoice.gross_total().amount),
        gib_number=invoice.gib_number,
        ettn=invoice.ettn,
    )


@router.post("/invoices", response_model=InvoiceResponse)
def compile_invoice(
    request: CompileInvoiceRequest,
    provider: Annotated[ExchangeRateProvider, Depends(get_exchange_rate_provider)],
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    """Angajman girdisinden Draft fatura derler, kaydeder ve döner.

    Var olan ve Draft olmayan bir fatura yeniden derlenemez (commit'li kayıt korunur).
    Kaynak girdiler düzenleme için saklanır.
    """
    existing = repository.get(request.invoice_id)
    if existing is not None and existing.status is not InvoiceStatus.Draft:
        raise HTTPException(status_code=409, detail="Onaylı/gönderilmiş fatura yeniden derlenemez")
    try:
        command = _to_command(request)
        invoice = CompileInvoice(provider).execute(command)
    except (ValueError, CurrencyMismatchError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    repository.save(invoice)
    repository.save_source(invoice.id, request.model_dump(mode="json"))
    return _to_response(invoice)


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> list[InvoiceResponse]:
    """Tüm kayıtlı faturaları döndürür."""
    return [_to_response(invoice) for invoice in repository.list_all()]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    """Kayıtlı faturayı id ile döndürür; yoksa 404."""
    invoice = repository.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadı: {invoice_id}")
    return _to_response(invoice)


def _transition(
    invoice_id: str,
    repository: InvoiceRepository,
    action: Callable[[Invoice], None],
) -> InvoiceResponse:
    invoice = repository.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadı: {invoice_id}")
    try:
        action(invoice)
    except InvoiceStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    repository.save(invoice)
    return _to_response(invoice)


@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceResponse)
def approve_invoice(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    """Taslak faturayı onaylar (Draft -> Approved)."""
    return _transition(invoice_id, repository, lambda invoice: invoice.approve())


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceResponse)
def send_invoice(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    """Onaylı faturayı gönderir (Approved -> Sent), entegratör olmadan."""
    return _transition(invoice_id, repository, lambda invoice: invoice.send())


@router.post("/invoices/{invoice_id}/issue", response_model=InvoiceResponse)
def issue_einvoice(
    invoice_id: str,
    request: IssueEInvoiceRequest,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    gateway: Annotated[EInvoiceGateway, Depends(get_einvoice_gateway)],
    supplier: Annotated[Party, Depends(get_einvoice_supplier)],
    series: Annotated[str, Depends(get_invoice_series)],
) -> InvoiceResponse:
    """Onaylı faturayı entegratöre e-Fatura/e-Arşiv olarak keser.

    Resmi GİB numarası (seri + yıl + sıra) burada atanır ve faturaya yazılır;
    gönderim başarısız olursa numara faturada kalır (yeniden deneme aynı numarayı
    kullanır, ardışıklık korunur). Başarıda fatura Sent'e geçer, ETTN kaydedilir.
    Onaylı değilse 409, iş kuralı reddi 422, taşıma/SOAP hatası 502.
    """
    invoice = repository.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadı: {invoice_id}")
    if invoice.status is not InvoiceStatus.Approved:
        raise HTTPException(status_code=409, detail="Yalnız onaylı fatura e-Fatura kesilebilir")

    # Numarayı yalnız ilk kez ata; başarısız gönderim sonrası retry'da yeniden kullan.
    if invoice.gib_number is None:
        sequence = repository.next_invoice_sequence(series, invoice.issue_date.year)
        invoice.gib_number = GibInvoiceNumber.from_parts(
            series, invoice.issue_date.year, sequence
        ).value
        repository.save(invoice)

    customer = Party(**request.customer.model_dump())
    command = IssueEInvoiceCommand(
        customer=customer,
        supplier=supplier,
        gib_number=invoice.gib_number,
        customer_alias=request.customer_alias,
    )
    try:
        result = IssueEInvoice(gateway).execute(invoice, command)
    except EInvoiceIssueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EInvoiceGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not result.succeeded:
        raise HTTPException(status_code=422, detail=result.message or "Fatura kesilemedi")
    invoice.send(ettn=result.ettn)
    repository.save(invoice)
    return _to_response(invoice)


def _require_issued(invoice_id: str, repository: InvoiceRepository) -> Invoice:
    invoice = repository.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadı: {invoice_id}")
    if not invoice.ettn:
        raise HTTPException(status_code=409, detail="Bu fatura henüz e-Fatura olarak kesilmedi")
    return invoice


@router.get("/invoices/{invoice_id}/einvoice-status", response_model=EInvoiceStatusResponse)
def einvoice_status(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    gateway: Annotated[EInvoiceGateway, Depends(get_einvoice_gateway)],
) -> EInvoiceStatusResponse:
    """Kesilmiş faturanın entegratör/GİB durumunu + işleme günlüklerini döndürür."""
    invoice = _require_issued(invoice_id, repository)
    try:
        status = gateway.get_invoice_status(invoice.ettn)
    except EInvoiceGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return EInvoiceStatusResponse(
        invoice_id=status.invoice_id,
        local_document_id=status.local_document_id,
        status=status.status,
        status_code=status.status_code,
        message=status.message,
        logs=[
            EInvoiceStatusLogOut(created_at=log.created_at, type=log.type, message=log.message)
            for log in status.logs
        ],
    )


@router.get("/invoices/{invoice_id}/einvoice-pdf")
def einvoice_pdf(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    gateway: Annotated[EInvoiceGateway, Depends(get_einvoice_gateway)],
) -> Response:
    """Kesilmiş faturanın PDF'ini döndürür (application/pdf)."""
    invoice = _require_issued(invoice_id, repository)
    try:
        pdf = gateway.get_invoice_pdf(invoice.ettn)
    except EInvoiceGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice_id}.pdf"'},
    )


@router.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> None:
    """Taslak faturayı siler. Yoksa 404; Draft değilse 409 (commit'li kayıt)."""
    invoice = repository.get(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadı: {invoice_id}")
    if invoice.status is not InvoiceStatus.Draft:
        raise HTTPException(status_code=409, detail="Yalnız taslak fatura silinebilir")
    repository.delete(invoice_id)


@router.get("/invoices/{invoice_id}/source", response_model=CompileInvoiceRequest)
def get_invoice_source(
    invoice_id: str,
    repository: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> CompileInvoiceRequest:
    """Faturanın kaynak girdilerini döndürür (düzenleme için); yoksa 404."""
    source = repository.get_source(invoice_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Kaynak girdiler bulunamadı: {invoice_id}")
    return CompileInvoiceRequest(**source)
