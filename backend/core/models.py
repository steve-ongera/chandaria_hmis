from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser


# ---------------------------------------------------------------------------
# USERS / RBAC
# ---------------------------------------------------------------------------

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        DOCTOR = "DOCTOR", "Doctor"
        NURSE = "NURSE", "Nurse"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.NURSE)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


# ---------------------------------------------------------------------------
# LOOKUP / REFERENCE TABLES (managed by admin, reused everywhere)
# ---------------------------------------------------------------------------

class ConsultationType(models.Model):
    """E.g. General Consultation, Specialist, Antenatal - each charged differently."""
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.price}"


class ICD10Code(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.description}"


class DiagnosisNote(models.Model):
    """Predefined service/diagnosis notes with a default amount, e.g. 'Wound cleaning'.
    Doctor picks from here instead of typing free text each time; can still override
    the amount or add a custom note when truly needed."""
    title = models.CharField(max_length=150, unique=True)
    default_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.default_amount})"


class Medicine(models.Model):
    class Unit(models.TextChoices):
        TABLET = "TABLET", "Tablet"
        STRIP = "STRIP", "Strip"
        BOTTLE = "BOTTLE", "Bottle"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=150)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.TABLET)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"


# ---------------------------------------------------------------------------
# PATIENT / VISIT
# ---------------------------------------------------------------------------

class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.phone}"


class Visit(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        TRIAGED = "TRIAGED", "Triaged"
        QUEUED = "QUEUED", "Queued"
        IN_CONSULTATION = "IN_CONSULTATION", "In Consultation"
        COMPLETED = "COMPLETED", "Completed"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    consultation_type = models.ForeignKey(ConsultationType, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REGISTERED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="visits_created")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visit #{self.id} - {self.patient} ({self.status})"


class Triage(models.Model):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name="triage")
    nurse = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    blood_pressure = models.CharField(max_length=20, blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse = models.PositiveIntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Triage for {self.visit}"


# ---------------------------------------------------------------------------
# CONSULTATION
# ---------------------------------------------------------------------------

class Consultation(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name="consultation")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="consultations")
    icd10_codes = models.ManyToManyField(ICD10Code, blank=True, related_name="consultations")
    diagnosis_notes = models.ManyToManyField(DiagnosisNote, through="ConsultationNote", blank=True)
    clinical_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def consultation_fee(self):
        return self.visit.consultation_type.price

    @property
    def notes_total(self):
        return sum((cn.amount for cn in self.consultation_notes.all()), 0)

    @property
    def medicine_total(self):
        return sum((p.subtotal for p in self.prescriptions.all()), 0)

    @property
    def grand_total(self):
        return self.consultation_fee + self.notes_total + self.medicine_total

    def __str__(self):
        return f"Consultation for {self.visit}"


class ConsultationNote(models.Model):
    """Through-model: a diagnosis/service note attached to a consultation, with the
    actual amount charged (defaults to the note's default_amount but can be edited,
    or a fully custom note+amount can be added)."""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="consultation_notes")
    diagnosis_note = models.ForeignKey(DiagnosisNote, on_delete=models.SET_NULL, null=True, blank=True)
    custom_title = models.CharField(max_length=150, blank=True)  # used only if no diagnosis_note picked
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def title(self):
        return self.diagnosis_note.title if self.diagnosis_note else self.custom_title

    def __str__(self):
        return f"{self.title} - {self.amount}"


class Prescription(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="prescriptions")
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    dispensed = models.BooleanField(default=False)
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="dispensed_prescriptions")
    dispensed_at = models.DateTimeField(null=True, blank=True)

    @property
    def subtotal(self):
        return self.medicine.unit_price * self.quantity

    def __str__(self):
        return f"{self.medicine} x{self.quantity}"


# ---------------------------------------------------------------------------
# PAYMENTS
# ---------------------------------------------------------------------------

class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        MPESA = "MPESA", "M-Pesa"
        CARD = "CARD", "Card"
        INSURANCE = "INSURANCE", "Insurance"

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.visit}"


# ---------------------------------------------------------------------------
# WALK-IN SALES (no patient / consultation needed)
# ---------------------------------------------------------------------------

class WalkInSale(models.Model):
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    customer_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        return sum((item.subtotal for item in self.items.all()), 0)

    def __str__(self):
        return f"WalkIn Sale #{self.id}"


class WalkInSaleItem(models.Model):
    sale = models.ForeignKey(WalkInSale, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.medicine.unit_price * self.quantity

    def __str__(self):
        return f"{self.medicine} x{self.quantity}"
