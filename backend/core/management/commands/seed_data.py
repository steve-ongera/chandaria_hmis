"""
Management command to seed the HMS database with ~6 months of realistic
Kenyan hospital data: users, reference data, patients, visits, triage,
consultations, prescriptions, payments, and walk-in sales.

Usage:
    python manage.py seed_data
    python manage.py seed_data --flush     # wipe existing data first
"""
import random
from datetime import timedelta, date

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from core.models import (
    User, ConsultationType, ICD10Code, DiagnosisNote, Medicine,
    Patient, Visit, Triage, Consultation, ConsultationNote,
    Prescription, Payment, WalkInSale, WalkInSaleItem,
)


# ---------------------------------------------------------------------------
# KENYAN REFERENCE DATA
# ---------------------------------------------------------------------------

FIRST_NAMES_M = [
    "Brian", "Kevin", "Dennis", "Collins", "Felix", "Erick", "Patrick", "Samuel",
    "Peter", "John", "James", "David", "Joseph", "Daniel", "Stephen", "Anthony",
    "Mwangi", "Otieno", "Kiplagat", "Wafula", "Kamau", "Njoroge", "Onyango",
    "Mutiso", "Kibet", "Barasa", "Omondi", "Wekesa", "Cheruiyot", "Mburu",
]

FIRST_NAMES_F = [
    "Mercy", "Faith", "Grace", "Joyce", "Mary", "Esther", "Lilian", "Caroline",
    "Beatrice", "Catherine", "Ann", "Nancy", "Eunice", "Susan", "Brenda", "Sharon",
    "Wanjiru", "Achieng", "Chebet", "Nafula", "Wairimu", "Akinyi", "Jepkosgei",
    "Naliaka", "Moraa", "Wambui", "Atieno", "Nyambura", "Kerubo", "Adhiambo",
]

LAST_NAMES = [
    "Mwangi", "Otieno", "Kamau", "Njoroge", "Onyango", "Mutiso", "Kibet",
    "Barasa", "Omondi", "Wekesa", "Cheruiyot", "Mburu", "Wanjiru", "Achieng",
    "Chebet", "Nafula", "Wairimu", "Akinyi", "Korir", "Maina", "Ochieng",
    "Kiprotich", "Wamalwa", "Gitau", "Mutua", "Ndungu", "Owino", "Rotich",
    "Simiyu", "Karanja",
]

# Safaricom / Airtel style Kenyan phone prefixes
PHONE_PREFIXES = ["0701", "0702", "0710", "0712", "0720", "0721", "0722",
                   "0728", "0733", "0740", "0742", "0758", "0768", "0790", "0795"]

NAIROBI_AREAS = [
    "Kasarani, Nairobi", "Embakasi, Nairobi", "Kibera, Nairobi", "Westlands, Nairobi",
    "Dagoretti, Nairobi", "Ruaraka, Nairobi", "Roysambu, Nairobi", "Langata, Nairobi",
    "Kawangware, Nairobi", "Umoja, Nairobi", "Donholm, Nairobi", "Githurai, Nairobi",
    "Kiambu Town, Kiambu", "Thika, Kiambu", "Ruiru, Kiambu", "Nakuru Town, Nakuru",
    "Eldoret Town, Uasin Gishu", "Kisumu City, Kisumu", "Machakos Town, Machakos",
    "Naivasha, Nakuru", "Kitengela, Kajiado", "Ngong, Kajiado",
]

CONSULTATION_TYPES = [
    ("General Consultation", 500),
    ("Specialist Consultation", 1500),
    ("Antenatal Consultation", 800),
    ("Pediatric Consultation", 700),
    ("Follow-up Visit", 300),
    ("Dental Consultation", 1000),
]

ICD10_CODES = [
    ("J00", "Acute nasopharyngitis (common cold)"),
    ("J18.9", "Pneumonia, unspecified organism"),
    ("A09", "Infectious gastroenteritis and colitis, unspecified"),
    ("B54", "Unspecified malaria"),
    ("A00-A09", "Malaria, confirmed by microscopy"),
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential (primary) hypertension"),
    ("K29.7", "Gastritis, unspecified"),
    ("J03.9", "Acute tonsillitis, unspecified"),
    ("N39.0", "Urinary tract infection, site not specified"),
    ("M54.5", "Low back pain"),
    ("R50.9", "Fever, unspecified"),
    ("J45.9", "Asthma, unspecified"),
    ("L08.9", "Local skin and subcutaneous infection, unspecified"),
    ("S01.9", "Open wound of head, unspecified"),
    ("O26.9", "Pregnancy related condition, unspecified"),
    ("B50", "Plasmodium falciparum malaria"),
    ("H66.9", "Otitis media, unspecified"),
    ("R51", "Headache"),
    ("T14.1", "Open wound, unspecified body region"),
]

DIAGNOSIS_NOTES = [
    ("Wound cleaning and dressing", 300),
    ("Minor wound suturing", 800),
    ("Injection administration", 150),
    ("Nebulization", 400),
    ("Normal delivery", 8000),
    ("Caesarean section", 35000),
    ("Minor surgical procedure", 5000),
    ("Catheterization", 600),
    ("ECG", 1000),
    ("Ultrasound scan", 1500),
    ("Plaster of Paris (POP) cast application", 2000),
    ("Removal of stitches", 200),
    ("Ear syringing", 350),
    ("Circumcision", 3000),
    ("IV fluid administration", 500),
]

MEDICINES = [
    ("Paracetamol 500mg", Medicine.Unit.TABLET, 5, 2000),
    ("Amoxicillin 500mg", Medicine.Unit.STRIP, 80, 500),
    ("Ibuprofen 400mg", Medicine.Unit.TABLET, 8, 1500),
    ("Artemether/Lumefantrine (Coartem)", Medicine.Unit.STRIP, 150, 600),
    ("Metronidazole 400mg", Medicine.Unit.TABLET, 6, 1200),
    ("Amoxiclav 625mg", Medicine.Unit.STRIP, 250, 400),
    ("Cetirizine 10mg", Medicine.Unit.TABLET, 5, 1000),
    ("Diclofenac 50mg", Medicine.Unit.TABLET, 7, 1000),
    ("ORS (Oral Rehydration Salts)", Medicine.Unit.OTHER, 50, 800),
    ("Zinc Sulphate Syrup", Medicine.Unit.BOTTLE, 180, 200),
    ("Cough Syrup (Bromhexine)", Medicine.Unit.BOTTLE, 220, 250),
    ("Omeprazole 20mg", Medicine.Unit.STRIP, 120, 400),
    ("Ciprofloxacin 500mg", Medicine.Unit.TABLET, 15, 800),
    ("Hydrocortisone Cream", Medicine.Unit.OTHER, 250, 150),
    ("Multivitamin Syrup", Medicine.Unit.BOTTLE, 300, 300),
    ("Salbutamol Inhaler", Medicine.Unit.OTHER, 600, 100),
    ("Folic Acid 5mg", Medicine.Unit.TABLET, 3, 3000),
    ("Ferrous Sulphate (Iron tablets)", Medicine.Unit.TABLET, 4, 2500),
    ("Metformin 500mg", Medicine.Unit.TABLET, 6, 1500),
    ("Amlodipine 5mg", Medicine.Unit.TABLET, 8, 1200),
    ("Antiseptic Solution (Dettol/Savlon)", Medicine.Unit.BOTTLE, 350, 150),
    ("Gauze and Bandages (pack)", Medicine.Unit.OTHER, 200, 300),
]

DOCTORS = [
    ("dr.kamau", "Peter", "Kamau"),
    ("dr.achieng", "Faith", "Achieng"),
    ("dr.mutiso", "Samuel", "Mutiso"),
    ("dr.wanjiru", "Grace", "Wanjiru"),
]

NURSES = [
    ("nurse.njeri", "Mercy", "Njeri"),
    ("nurse.otieno", "Brenda", "Otieno"),
    ("nurse.kiplagat", "Esther", "Kiplagat"),
]


def random_phone():
    return f"{random.choice(PHONE_PREFIXES)}{random.randint(100000, 999999)}"


def random_date_of_birth():
    start = date(1945, 1, 1)
    end = date(2023, 1, 1)
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


class Command(BaseCommand):
    help = "Seed the HMS database with ~6 months of realistic Kenyan hospital data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing seedable data before generating new data.",
        )
        parser.add_argument(
            "--patients", type=int, default=150,
            help="Number of unique patients to create (default: 150).",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            WalkInSaleItem.objects.all().delete()
            WalkInSale.objects.all().delete()
            Payment.objects.all().delete()
            Prescription.objects.all().delete()
            ConsultationNote.objects.all().delete()
            Consultation.objects.all().delete()
            Triage.objects.all().delete()
            Visit.objects.all().delete()
            Patient.objects.all().delete()

        with transaction.atomic():
            doctors = self._seed_users(DOCTORS, User.Role.DOCTOR)
            nurses = self._seed_users(NURSES, User.Role.NURSE)
            self._seed_admin()

            consultation_types = self._seed_consultation_types()
            icd10_codes = self._seed_icd10()
            diagnosis_notes = self._seed_diagnosis_notes()
            medicines = self._seed_medicines()

            patients = self._seed_patients(options["patients"])
            self._seed_visits(
                patients=patients, doctors=doctors, nurses=nurses,
                consultation_types=consultation_types, icd10_codes=icd10_codes,
                diagnosis_notes=diagnosis_notes, medicines=medicines,
            )
            self._seed_walkin_sales(nurses=nurses, medicines=medicines)

        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------

    def _seed_users(self, people, role):
        users = []
        for username, first, last in people:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "role": role},
            )
            if created:
                user.set_password("password123")
                user.save()
            users.append(user)
        self.stdout.write(f"  {role.title()}s ready: {len(users)}")
        return users

    def _seed_admin(self):
        if not User.objects.filter(username="admin").exists():
            admin = User.objects.create_superuser(
                username="admin", email="admin@hospital.co.ke", password="admin12345"
            )
            admin.role = User.Role.ADMIN
            admin.save()
            self.stdout.write("  Admin user created (admin / admin12345)")

    # ------------------------------------------------------------------
    # REFERENCE DATA
    # ------------------------------------------------------------------

    def _seed_consultation_types(self):
        objs = []
        for name, price in CONSULTATION_TYPES:
            obj, _ = ConsultationType.objects.get_or_create(name=name, defaults={"price": price})
            objs.append(obj)
        self.stdout.write(f"  Consultation types: {len(objs)}")
        return objs

    def _seed_icd10(self):
        objs = []
        for code, desc in ICD10_CODES:
            obj, _ = ICD10Code.objects.get_or_create(code=code, defaults={"description": desc})
            objs.append(obj)
        self.stdout.write(f"  ICD-10 codes: {len(objs)}")
        return objs

    def _seed_diagnosis_notes(self):
        objs = []
        for title, amount in DIAGNOSIS_NOTES:
            obj, _ = DiagnosisNote.objects.get_or_create(title=title, defaults={"default_amount": amount})
            objs.append(obj)
        self.stdout.write(f"  Diagnosis notes: {len(objs)}")
        return objs

    def _seed_medicines(self):
        objs = []
        for name, unit, price, stock in MEDICINES:
            obj, created = Medicine.objects.get_or_create(
                name=name, defaults={"unit": unit, "unit_price": price, "stock_quantity": stock}
            )
            if not created:
                # top up stock so 6 months of dispensing/sales doesn't run dry
                obj.stock_quantity = max(obj.stock_quantity, stock)
                obj.save(update_fields=["stock_quantity"])
            objs.append(obj)
        self.stdout.write(f"  Medicines: {len(objs)}")
        return objs

    # ------------------------------------------------------------------
    # PATIENTS
    # ------------------------------------------------------------------

    def _seed_patients(self, count):
        patients = list(Patient.objects.all())
        existing_phones = {p.phone for p in patients}
        created = 0
        while created < count:
            gender = random.choice(["M", "F"])
            first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
            last = random.choice(LAST_NAMES)
            phone = random_phone()
            if phone in existing_phones:
                continue
            existing_phones.add(phone)
            patient = Patient.objects.create(
                first_name=first,
                last_name=last,
                phone=phone,
                gender=gender,
                date_of_birth=random_date_of_birth(),
                national_id=str(random.randint(20000000, 39999999)),
                address=random.choice(NAIROBI_AREAS),
            )
            patients.append(patient)
            created += 1
        self.stdout.write(f"  Patients: {len(patients)} (new: {created})")
        return patients

    # ------------------------------------------------------------------
    # VISITS / TRIAGE / CONSULTATIONS / PRESCRIPTIONS / PAYMENTS
    # ------------------------------------------------------------------

    def _seed_visits(self, patients, doctors, nurses, consultation_types,
                      icd10_codes, diagnosis_notes, medicines):
        now = timezone.now()
        six_months_ago = now - timedelta(days=182)

        visit_count = 0
        total_days = 182

        for day_offset in range(total_days):
            day = six_months_ago + timedelta(days=day_offset)
            # Sundays are quieter; skip some days entirely for realism
            if day.weekday() == 6 and random.random() < 0.5:
                continue

            visits_today = random.randint(2, 9)
            for _ in range(visits_today):
                patient = random.choice(patients)
                consultation_type = random.choice(consultation_types)
                nurse = random.choice(nurses)
                doctor = random.choice(doctors)

                visit_time = day.replace(
                    hour=random.randint(8, 16),
                    minute=random.randint(0, 59),
                    second=0, microsecond=0,
                )

                visit = Visit.objects.create(
                    patient=patient,
                    consultation_type=consultation_type,
                    status=Visit.Status.COMPLETED,
                    created_by=nurse,
                )
                Visit.objects.filter(pk=visit.pk).update(created_at=visit_time)

                # ---------------- Triage ----------------
                triage_time = visit_time + timedelta(minutes=random.randint(5, 20))
                triage = Triage.objects.create(
                    visit=visit,
                    nurse=nurse,
                    blood_pressure=f"{random.randint(100, 140)}/{random.randint(60, 90)}",
                    temperature=round(random.uniform(36.0, 39.5), 1),
                    pulse=random.randint(60, 110),
                    weight=round(random.uniform(8.0, 95.0), 1),
                    height=round(random.uniform(50.0, 190.0), 1),
                    notes=random.choice([
                        "Patient reports mild discomfort.",
                        "No known allergies.",
                        "Patient appears stable.",
                        "Complains of fatigue.",
                        "Mild fever noted on arrival.",
                        "",
                    ]),
                )
                Triage.objects.filter(pk=triage.pk).update(recorded_at=triage_time)

                # ---------------- Consultation ----------------
                consult_time = triage_time + timedelta(minutes=random.randint(10, 60))
                consultation = Consultation.objects.create(
                    visit=visit,
                    doctor=doctor,
                    clinical_notes=random.choice([
                        "Patient presented with symptoms consistent with diagnosis. Advised rest and medication.",
                        "Reviewed patient history. Prescribed treatment as below.",
                        "Follow-up recommended in 7 days if symptoms persist.",
                        "Patient counselled on medication adherence.",
                        "Vitals stable. Treatment plan discussed with patient.",
                    ]),
                    status=Consultation.Status.COMPLETED,
                )
                completed_time = consult_time + timedelta(minutes=random.randint(10, 30))
                Consultation.objects.filter(pk=consultation.pk).update(
                    started_at=consult_time, completed_at=completed_time
                )
                consultation.icd10_codes.set(random.sample(icd10_codes, k=random.randint(1, 2)))

                # Occasionally add a service/diagnosis note (wound cleaning, delivery, etc.)
                if random.random() < 0.25:
                    note = random.choice(diagnosis_notes)
                    ConsultationNote.objects.create(
                        consultation=consultation,
                        diagnosis_note=note,
                        amount=note.default_amount,
                    )

                # Prescriptions
                num_meds = random.randint(1, 3)
                for medicine in random.sample(medicines, k=min(num_meds, len(medicines))):
                    qty = random.randint(1, 2) if medicine.unit == Medicine.Unit.STRIP else random.randint(1, 30)
                    dispensed = random.random() < 0.85
                    Prescription.objects.create(
                        consultation=consultation,
                        medicine=medicine,
                        quantity=qty,
                        dispensed=dispensed,
                        dispensed_by=nurse if dispensed else None,
                        dispensed_at=completed_time + timedelta(minutes=15) if dispensed else None,
                    )

                # ---------------- Payment ----------------
                grand_total = consultation.grand_total
                if random.random() < 0.93:  # most visits get paid
                    Payment.objects.create(
                        visit=visit,
                        amount=grand_total,
                        method=random.choices(
                            [Payment.Method.CASH, Payment.Method.MPESA,
                             Payment.Method.CARD, Payment.Method.INSURANCE],
                            weights=[20, 55, 10, 15],
                        )[0],
                        recorded_by=nurse,
                    )

                visit_count += 1

        self.stdout.write(f"  Visits (with triage + consultation): {visit_count}")

    # ------------------------------------------------------------------
    # WALK-IN SALES (no consultation, e.g. over-the-counter purchases)
    # ------------------------------------------------------------------

    def _seed_walkin_sales(self, nurses, medicines):
        now = timezone.now()
        six_months_ago = now - timedelta(days=182)
        sale_count = 0

        for day_offset in range(182):
            if random.random() < 0.6:  # not every day has walk-in sales
                continue
            day = six_months_ago + timedelta(days=day_offset)
            num_sales = random.randint(1, 4)
            for _ in range(num_sales):
                nurse = random.choice(nurses)
                sale_time = day.replace(
                    hour=random.randint(8, 18), minute=random.randint(0, 59),
                    second=0, microsecond=0,
                )
                sale = WalkInSale.objects.create(
                    sold_by=nurse,
                    customer_name=random.choice([
                        "", "", f"{random.choice(FIRST_NAMES_M + FIRST_NAMES_F)} {random.choice(LAST_NAMES)}",
                    ]),
                )
                WalkInSale.objects.filter(pk=sale.pk).update(created_at=sale_time)

                for medicine in random.sample(medicines, k=random.randint(1, 2)):
                    qty = random.randint(1, 2) if medicine.unit == Medicine.Unit.STRIP else random.randint(1, 10)
                    WalkInSaleItem.objects.create(sale=sale, medicine=medicine, quantity=qty)

                sale_count += 1

        self.stdout.write(f"  Walk-in sales: {sale_count}")