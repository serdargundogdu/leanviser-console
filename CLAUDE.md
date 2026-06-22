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
  tests/                          # pytest (health + framework-süz domain + adapter testleri)
frontend/                         # Vite + React + TS; /finance fatura derleme/kesme UI
.github/workflows/                # ci.yml (ruff+pytest+build), deploy.yml (Cloud Run, secret-gated)
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
| KDV oranı | `VatRate` (kalem bazında; net üzerinden `vatAmount`) |
| e-Fatura / e-Arşiv | `e-invoice` / `e-archive` (UBL profili: `TICARIFATURA` / `EARSIVFATURA`) |
| GİB Fatura Numarası | `GibInvoiceNumber` (16 hane: seri+yıl+sıra; UBL `cbc:ID`) |
| ETTN | `ettn` (entegratörce atanan e-belge kimliği/UUID) |
| Alıcı Etiketi (PK) | `alias` (GİB posta kutusu; e-Fatura yönlendirme hedefi) |
| Özel Entegratör | `EInvoiceGateway` port'u (Uyumsoft; CAPTCHA'sız SOAP — e-Devlet API'si değil) |
| Anti-Corruption Layer | `ACL` (dış sistem adapter'ı; çekirdeği kirletmez) |

## Tamamlanan dikey dilimler (finance)

> Bu bölüm "ne hazır" özetidir; ayrıntı kod ve commit geçmişindedir.

- **Bedel Hesaplama (Core, temel):** `Money`/`Currency` VO (Decimal, float yok), `VatRate`,
  `ExchangeRate`/`FeeCalculation` (birim-önce TRY dönüşümü), kalem bazında KDV (net/KDV/brüt).
- **Invoice aggregate:** `InvoiceLine` (KDV oranlı), durum makinesi Draft → Approved → Sent,
  `CompileInvoice` use case.
- **TCMB ACL:** `TcmbExchangeRateProvider` (canlı kur; yayınlanmamış günde önceki iş gününe düşer).
- **Uyumsoft e-Fatura ACL (`EInvoiceGateway` port'u):** bağlantı, **gönderim** (UBL-TR +
  `SendInvoice`, WSSE), **durum + günlük**, **PDF**, geçerli **GİB numarası üretimi** (seri+yıl+sıra,
  atomik sayaç), **otomatik e-Fatura/e-Arşiv yönlendirme** (alıcı etiketi `GetUserAliasses` ile).
  Hepsi test endpoint'inde uçtan uca doğrulandı. Prod yalnız env ile açılır.
- **HTTP + Frontend:** `/finance` derleme/onay/**kesme**/durum/PDF/düzenle/sil akışı (TR biçim).
- **Kalıcılık:** SQLite (yerel) + Postgres/Cloud SQL (prod) — aynı `InvoiceRepository` port'u.

### Konfigürasyon (env; varsayılanlar herkese açık TEST'tir)

- `DATABASE_URL` → Postgres (yoksa yerel SQLite).
- `UYUMSOFT_USERNAME` / `UYUMSOFT_PASSWORD`, `UYUMSOFT_ENV=live` → canlı entegratör.
- `LEANVISER_VKN` / `LEANVISER_NAME` / … → gerçek gönderici kimliği; `LEANVISER_INVOICE_SERIES` (vars. `LVS`).

## Prod dağıtımı (canlı)

> Tek **Cloud Run** servisi hem derlenmiş SPA'yı hem API'yi sunar (tek origin; API `/api`
> altında, kalan yollar SPA index.html). Kök `Dockerfile` (Cloud Build) ikisini de derler.

- **GCP projesi:** `leanviser-console` (no `946068546869`), bölge `europe-west1`, org `leanviser.com`.
- **Servis:** `leanviser-console-backend` — `--no-allow-unauthenticated` (güvenli varsayılan; anonim → 403).
- **CI/CD:** `main`'e push → `deploy.yml`. Kimlik doğrulama **anahtarsız (WIF/OIDC)** —
  org politikası SA anahtarını yasaklar (`iam.disableServiceAccountKeyCreation`). Deployer SA
  `gha-deployer@…`; repo-kısıtlı WIF provider. GitHub secret'ları: `GCP_PROJECT`, `GCP_REGION`,
  `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`, `CLOUDSQL_INSTANCE`.
- **Kalıcılık:** Cloud SQL Postgres `leanviser-console-db`; `DATABASE_URL` Secret Manager'da
  (Cloud SQL socket DSN), runtime SA `secretAccessor` + `cloudsql.client`. Uçtan uca doğrulandı.
- **Entegratör:** şimdilik **TEST** (canlı için `UYUMSOFT_LIVE=true` + creds secret'ları + gerçek `LEANVISER_VKN`).
- **Erişim (canlı):** `https://console.leanviser.app` → Cloud Run **domain mapping** (Google-yönetimli
  SSL) → servise **doğrudan IAP** (Google-yönetimli OAuth; eski IAP brand/oauth API'si Mart 2026'da
  kapandı, manuel client gerekmedi). Domain `leanviser.app` GoDaddy'de; `console` CNAME →
  `ghs.googlehosted.com`. Yalnız **`roles/iap.httpsResourceAccessor` verilen kullanıcılar** girer
  (şu an `serdargundogdu@`, `canyukselen@`). IAP servise `--iap` ile açıldı; harici HTTPS LB
  **gerekmedi** (domain mapping + doğrudan IAP yeterli). run.app URL'i de IAP arkasında (anonim → giriş).
  - IAP üye yönetimi: `gcloud iap web {add,remove}-iam-policy-binding --resource-type=cloud-run --service=leanviser-console-backend --region=europe-west1 --member=user:… --role=roles/iap.httpsResourceAccessor`.
- **Cloud Build notu:** klasik docker builder (BuildKit'siz); Dockerfile'da `RUN --mount` kullanma.

## Kapsam dışı (sonraki turlar)

- **İleri KDV senaryoları:** tevkifat, istisna, çok-oranlı matrah ayrıştırması (temel KDV hazır).
- **Google Calendar** entegrasyonu → ileride ACL port'u olarak. (Uyumsoft ve TCMB ACL'leri **tamam**.)
- **e-Fatura iyileştirmeleri:** birden çok alıcı etiketi arasında seçim, gelen kutusu (inbox) akışı.
- Auth / multi-tenant → tek-kiracılı olduğu için gereksiz.
