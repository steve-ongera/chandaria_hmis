# Hospital Management System (HMS)

A simple Hospital Management System with **Role-Based Access Control (RBAC)** for
**Nurses** (acting as receptionists + triage + dispensing) and **Doctors**
(consultation, diagnosis, prescription).

Backend: **Django + Django REST Framework** (single app: `core`)
Frontend: **Next.js**

---

## How the system works (flow)

A patient walks into the hospital. The **nurse**, acting as receptionist, searches
for the patient by name/phone/ID number. If the patient does not exist, the nurse
registers them once (name, phone, DOB, gender, etc.) — this creates a permanent
**Patient** record. Every time that same patient comes back, instead of registering
them again, the nurse simply creates a new **Visit** for the existing patient. After
a visit is created, the nurse performs **Triage** (BP, temperature, pulse, weight,
height, notes) and the visit is automatically pushed into the **consultation queue**.

In the **consultation room**, the doctor sees a live queue of waiting patients. The
doctor picks the next patient and starts a **Consultation**. The system
automatically pulls in: the **consultation type** the patient is visiting for (each
type — General, Specialist, Antenatal, etc. — is charged differently), the
**triage data** recorded by the nurse, and a searchable list of **ICD-10 codes** to
attach as diagnosis. The doctor then writes a **prescription** by picking
**medicines already in the system** (with stock and unit type — tablet, strip, or
bottle — so the right quantity unit is used).

For extra clinical services that aren't simple medicine (e.g. wound cleaning,
dressing, minor procedure, delivery, operation), the doctor doesn't type free text
every time — the system stores a list of **common diagnosis/service notes** with a
**default amount**, the doctor selects from that list (or, only when truly
necessary, types a custom note + amount), so charges stay consistent across
doctors.

Once the doctor finishes, the patient is sent back to the **reception/nurse desk**.
The nurse sees the total bill (consultation fee + service notes + medicine cost),
collects payment, and **dispenses** the prescribed medicines from stock. The system
also supports **walk-in sales** (e.g. someone just buying medicine over the counter
without seeing a doctor) handled directly by the nurse.

---

## Roles (RBAC)

| Role   | Can do |
|--------|--------|
| Nurse  | Register patients, create visits, do triage, view queue, record payments, dispense medicine, walk-in sales |
| Doctor | View consultation queue, start/complete consultations, diagnose (ICD-10), add service notes, prescribe medicine |
| Admin  | Manage consultation types, medicines, ICD-10 codes, diagnosis notes, users |

---

## Project Structure

```
hms/
├── README.md
├── backend/
│   ├── manage.py
│   ├── hms_backend/                # project config
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py                 # main urls
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── core/                       # single core app
│       ├── __init__.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── permissions.py
│       ├── urls.py                 # app urls
│       └── admin.py
│
└── frontend/                       # Next.js app (pages router)
    ├── package.json
    ├── next.config.js
    ├── lib/
    │   └── api.js                  # axios client + auth + role helpers
    ├── styles/
    │   └── main.css                # all styling, no CSS framework needed
    ├── components/
    │   ├── Navbar.js                # top bar: app name, user, logout
    │   ├── Sidebar.js                # role-aware nav links (Doctor vs Nurse)
    │   └── Layout.js                 # wraps every page with Navbar + Sidebar, guards auth
    └── pages/                       # every route lives flat in here
        ├── _app.js                  # imports styles/main.css globally
        ├── _document.js             # loads Bootstrap Icons CDN
        ├── index.js                 # redirects to /reception or /queue based on role
        ├── login.js                 # login + role selector
        ├── reception.js             # nurse: patient search/register + create visit
        ├── triage.js                # nurse: triage form
        ├── billing.js               # nurse: bill breakdown, payment, dispensing
        ├── walkin.js                # nurse: walk-in medicine sale
        ├── queue.js                 # doctor: consultation queue
        └── consultation/
            └── [id].js               # doctor: consultation room
```

### Role-based sidebar

`Sidebar.js` reads the logged-in user's role (`NURSE` or `DOCTOR`, stored at login)
and shows a different set of links for each:

- **Nurse:** Reception, Triage, Billing & Dispensing, Walk-in Sale
- **Doctor:** Consultation Queue

The role only controls which links are *shown* — the backend (`IsNurse` /
`IsDoctor` permission classes) is what actually enforces access on every API call.

## Core data model (simplified)

```
Patient ──< Visit ──< Triage
                  ├──< Consultation ──< Prescription >── Medicine
                  │           ├──< ICD10Code (M2M)
                  │           └──< DiagnosisNote (M2M through ConsultationNote, with amount)
                  └──< Payment

WalkInSale ──< WalkInSaleItem >── Medicine   (no patient needed)
```

## Status flow of a Visit

```
registered → triaged → queued → in_consultation → completed
```
