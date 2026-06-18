# LeanViser CONSOLE — CLAUDE.md

> Bu dosya, sonraki Claude Code oturumlarının **ilk okuyacağı** kaynaktır.
> Kilitli kararları, dili ve çalışma yöntemini burada tutuyoruz. Değişmez bölümleri
> tek başına açma; belirsizlikte varsayımını yaz ve sor (AI önerir, insan onaylar).

## Proje kimliği (değişmez)

- **leanviser-console**, LeanViser'ın **iç operasyon uygulamasıdır** (İç Projeler).
- **TEK-KİRACILI**: yalnız LeanViser kullanır. Multi-tenant **YOK**. Bu nedenle bu aşamada **auth YOK**.
- İlk route: **finance** (`/finance`). İlk süreç: **fatura kesme**. Kök adres: `console.leanviser.app`.
- Bu bir **ERP/MES DEĞİL** — üretim/stok/makine verisi girmez.
- Dış sistemlerle (Google Calendar, Uyumsoft, TCMB) temas **YALNIZ ACL/adapter** üzerinden olur.
- Roller (kişi değil — KVKK gereği): **Consultant**, **FinanceOfficer**, **CustomerCompany**.

## Mimari (kilitli)

- Tek **modüler monolit**; her modül proje içinde bir route = **Bounded Context** (ayrı mikroservis değil).
- **Hexagonal (ports & adapters)** katmanlama:

  ```
  domain/        # saf iş kuralı; framework-süz; HTTP/DB/dış API bilmez
    ↑
  application/   # use case'ler; domain'i orkestra eder; port'ları tanımlar
    ↑
  adapters/      # FastAPI, DB, dış sistem ACL — port'ların somut karşılığı
  ```

- **Bağımlılık daima içe akar.** `adapters → application → domain`. Domain dışarıyı asla import etmez.
- İş kuralı **domain'de, aggregate'te** tutulur — **anemik model yok**.
- `domain/` ve `application/` **framework-süz birim test** edilir (FastAPI/DB gerektirmeden).

## Stack

| Katman | Seçim |
| --- | --- |
| Backend | Python 3.12 + FastAPI |
| Test | pytest |
| Lint/format | ruff |
| Bağımlılık yöneticisi | uv |
| Frontend | React + Vite + TypeScript |
| Dağıtım | GCP Cloud Run + GitHub Actions CI/CD; backend için çok aşamalı Dockerfile |

> **uv gerekçesi:** tek araçta hızlı çözümleme + kilitli `uv.lock` ile yeniden üretilebilir
> kurulum; Python sürümünü de yönetir (3.12'yi proje dışında sistem kurulumuna bağlamadan sabitler).

## Dil kuralı

- **Konuşma / yorum / dokümantasyon:** Türkçe.
- **Kod / tanımlayıcı / commit mesajı / DB şeması:** İngilizce.
- **UI metni (kullanıcıya görünen):** Türkçe.
- Adlar **Ubiquitous Language**'ten gelir (aşağıdaki tablo).

## Klasör yapısı

```
backend/
  app/
    main.py                       # FastAPI app; GET /health -> {"status":"ok"}
    shared/                       # ortak VO/yardımcılar (ileride Money vb.) — şimdilik iskelet
    modules/
      finance/                    # Bounded Context: finance
        domain/                   # saf iş kuralı
        application/              # use case + port
        adapters/                 # FastAPI/DB/ACL
  tests/                          # pytest (health + framework-süz domain testleri)
frontend/                         # Vite + React + TS; /finance placeholder
.github/workflows/                # ci.yml (ruff+pytest+build), deploy.yml (Cloud Run iskeleti)
```

## PDCA çalışma yöntemi

Küçük artımlarla (Kaizen) ilerle:

1. **Plan** — kısa plan + dokunulacak dosyalar; kilitli karar/yeni kapsam varsa **onay bekle**.
2. **Do** — uygula; küçük ve anlamlı (İngilizce) commit'ler; dokunduğun kodu biraz daha temiz bırak.
3. **Check** — `ruff` temiz, `pytest` yeşil, ilgili akış elle doğrulanır.
4. **Act** — özet: ne değişti, nasıl çalıştırılır, sıradaki aday.

Clean Code: küçük tek-sorumlu birimler; adlar Ubiquitous Language'ten; sihirli sabit yok.

## Ubiquitous Language (kod/DB İngilizce)

| Türkçe | İngilizce (kod/DB) |
| --- | --- |
| Danışman | `Consultant` |
| Mali İşler Sorumlusu | `FinanceOfficer` |
| Müşteri Firma | `CustomerCompany` |
| Masraf / net tutar | `Expense` / `netAmount` |
| Gün Sayısı | `consultantDays` |
| Günlük Ücret | `dailyRate` |
| Hizmet Bedeli | `serviceFee` |
| Döviz Kuru (TCMB alış) | `fxBuyRate` |
| Fatura / kalem / durum | `Invoice` / `InvoiceLine` / `InvoiceStatus` (Draft → Approved → Sent) |
| Fatura Taslağı / Onay | `InvoiceDraft` / `Approval` |
| Anti-Corruption Layer | `ACL` (dış sistem adapter'ı; çekirdeği kirletmez) |

## Kapsam dışı (sonraki turlar)

- **Bedel Hesaplama domain mantığı** (Money VO, KDV ayrıştırma, gün × ücret, döviz dönüşümü) → sonraki dilim (**Core**).
- **Google Calendar / Uyumsoft / TCMB** entegrasyonu → ileride ACL port'u olarak.
  (Not: `api.uyum.com.tr` e-Devlet API'sinde CAPTCHA var → tam otomasyon yok; ticari e-Dönüşüm e-Fatura/e-Arşiv API dokümanı gelince ele alınır.)
- Native masraf formu işlevi, kalıcılık/DB şeması → sonraki dikey dilim.
- Auth / multi-tenant → tek-kiracılı olduğu için gereksiz.
