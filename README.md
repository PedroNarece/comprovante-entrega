# ProofSnap — Delivery Receipt Capture & Validation

> 📦 Capture, validate and instantly share proof-of-delivery documents.

[![Live Demo](https://img.shields.io/badge/Demo-Online-brightgreen?style=for-the-badge&logo=render)](https://proofsnap-x8tx.onrender.com)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?style=for-the-badge&logo=google)](https://aistudio.google.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite)](https://sqlite.org)

🌐 **Aplicação no Ar (Mobile):** [https://proofsnap-x8tx.onrender.com](https://proofsnap-x8tx.onrender.com)  
📊 **Dashboard de Auditoria:** [https://proofsnap-x8tx.onrender.com/dashboard](https://proofsnap-x8tx.onrender.com/dashboard)

## The Problem

In wholesale distribution, drivers collect signed paper receipts ("canhotos") as proof of delivery. Where I work, the physical receipt only becomes available to office staff **after it returns to headquarters and is scanned — which can take weeks**. Until then, anyone who needs proof of a delivery (billing, customer disputes) simply has to wait, or ask the driver to send a photo over a messaging app.

That informal workaround reveals two things:

- The need for **immediate access** to proof of delivery is real — staff already request photos ad hoc.
- Drivers are **already willing** to photograph receipts — there is just no system to capture, validate and organize those photos.

The result today: photos arrive **blurry or unreadable** with no quality check, scattered across chat conversations, impossible to search by delivery, and dependent on someone remembering to ask.

I work in this operation and watch it happen every day. This project is my attempt to solve it properly.

## The Solution

A mobile-first application where the driver photographs the receipt at the moment of delivery. The app:

1. **Validates the photo on-device** (blur and framing check) and gives instant feedback — "retake this photo" — before any network is involved.
2. **Queues the upload offline-first**: photos are stored locally and synced automatically when connectivity returns, with retries.
3. **Validates the content server-side** with an AI vision step (is this actually a receipt? is the signature/date area present?).
4. **Publishes to a web dashboard** where office staff see receipts seconds after the delivery, organized by route, driver and date.

## Architecture (planned)

```
[ Mobile app ]                      [ Cloud ]
 capture photo                       object storage (photos)
 on-device legibility check    -->   API (upload, metadata)
 offline queue + retry               AI content validation
                                     web dashboard (office staff)
```

Key design decisions and trade-offs will be documented here as they are made.

## Roadmap

- [x] **v1 — End-to-end skeleton**: take photo → upload to cloud storage → simple web page listing photos by date. No offline support, no AI.
- [x] **v2 — Reliability**: offline queue with sync and retry, authentication, organization by route/driver/date.
- [x] **v3 — Intelligence**: server-side AI content validation, rejection metrics, dashboard with daily stats.
- [ ] **v4 — Operations**: structured logging, metrics (time from delivery to availability, upload failure rate), load simulation with concurrent drivers.

## Privacy by Design

Delivery receipts contain personal data (names, addresses, signatures). From v1 onwards this project follows privacy-by-design principles aligned with LGPD/GDPR: access control on the dashboard, defined data retention, and no real customer data is ever used during development — all test receipts are synthetic.

## Status

🌱 **Pre-development.** This README marks the starting point of the project. I am currently in the first year of my Computer Engineering degree; this project will grow alongside my studies, one layer per semester. Follow the commit history to watch it evolve.

## License

MIT
