from rest_framework import serializers
from django.db import transaction
from .models import (
    User, ConsultationType, ICD10Code, DiagnosisNote, Medicine,
    Patient, Visit, Triage, Consultation, ConsultationNote,
    Prescription, Payment, WalkInSale, WalkInSaleItem,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role"]


# ---------------- Lookup tables ----------------

class ConsultationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationType
        fields = ["id", "name", "price", "is_active"]


class ICD10CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICD10Code
        fields = ["id", "code", "description"]


class DiagnosisNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisNote
        fields = ["id", "title", "default_amount", "is_active"]


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ["id", "name", "unit", "unit_price", "stock_quantity"]


# ---------------- Patient / Visit ----------------

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "first_name", "last_name", "phone", "gender",
                  "date_of_birth", "national_id", "address", "created_at"]


class TriageSerializer(serializers.ModelSerializer):
    nurse = UserSerializer(read_only=True)

    class Meta:
        model = Triage
        fields = ["id", "visit", "nurse", "blood_pressure", "temperature",
                  "pulse", "weight", "height", "notes", "recorded_at"]
        read_only_fields = ["nurse"]

    def create(self, validated_data):
        validated_data["nurse"] = self.context["request"].user
        triage = super().create(validated_data)
        # move visit forward in the flow
        visit = triage.visit
        visit.status = Visit.Status.QUEUED
        visit.save(update_fields=["status"])
        return triage


class VisitSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source="patient", write_only=True
    )
    consultation_type = ConsultationTypeSerializer(read_only=True)
    consultation_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ConsultationType.objects.all(), source="consultation_type", write_only=True
    )
    triage = TriageSerializer(read_only=True)

    class Meta:
        model = Visit
        fields = ["id", "patient", "patient_id", "consultation_type", "consultation_type_id",
                  "status", "created_by", "created_at", "triage"]
        read_only_fields = ["status", "created_by", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


# ---------------- Consultation ----------------

class ConsultationNoteSerializer(serializers.ModelSerializer):
    title = serializers.ReadOnlyField()

    class Meta:
        model = ConsultationNote
        fields = ["id", "diagnosis_note", "custom_title", "amount", "title"]


class PrescriptionSerializer(serializers.ModelSerializer):
    medicine = MedicineSerializer(read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.all(), source="medicine", write_only=True
    )
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = Prescription
        fields = ["id", "consultation", "medicine", "medicine_id", "quantity",
                  "dispensed", "dispensed_by", "dispensed_at", "subtotal"]
        read_only_fields = ["dispensed", "dispensed_by", "dispensed_at"]


class ConsultationSerializer(serializers.ModelSerializer):
    doctor = UserSerializer(read_only=True)
    icd10_codes = ICD10CodeSerializer(many=True, read_only=True)
    icd10_code_ids = serializers.PrimaryKeyRelatedField(
        queryset=ICD10Code.objects.all(), many=True, write_only=True,
        source="icd10_codes", required=False
    )
    consultation_notes = ConsultationNoteSerializer(many=True, read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    consultation_fee = serializers.ReadOnlyField()
    notes_total = serializers.ReadOnlyField()
    medicine_total = serializers.ReadOnlyField()
    grand_total = serializers.ReadOnlyField()

    # convenience read-only fields pulled in automatically for the doctor's screen
    visit_consultation_type = serializers.CharField(source="visit.consultation_type.name", read_only=True)
    visit_triage = TriageSerializer(source="visit.triage", read_only=True)

    class Meta:
        model = Consultation
        fields = ["id", "visit", "doctor", "icd10_codes", "icd10_code_ids",
                  "diagnosis_notes", "consultation_notes", "clinical_notes",
                  "prescriptions", "status", "started_at", "completed_at",
                  "consultation_fee", "notes_total", "medicine_total", "grand_total",
                  "visit_consultation_type", "visit_triage"]
        read_only_fields = ["doctor", "status", "started_at", "completed_at"]

    def create(self, validated_data):
        validated_data["doctor"] = self.context["request"].user
        icd10_codes = validated_data.pop("icd10_codes", [])
        with transaction.atomic():
            consultation = Consultation.objects.create(**validated_data)
            if icd10_codes:
                consultation.icd10_codes.set(icd10_codes)
            visit = consultation.visit
            visit.status = Visit.Status.IN_CONSULTATION
            visit.save(update_fields=["status"])
        return consultation


class CompleteConsultationSerializer(serializers.Serializer):
    """Used on the 'complete' action: marks consultation + visit done."""

    def save(self, **kwargs):
        consultation = self.context["consultation"]
        from django.utils import timezone
        consultation.status = Consultation.Status.COMPLETED
        consultation.completed_at = timezone.now()
        consultation.save(update_fields=["status", "completed_at"])
        visit = consultation.visit
        visit.status = Visit.Status.COMPLETED
        visit.save(update_fields=["status"])
        return consultation


# ---------------- Payments ----------------

class PaymentSerializer(serializers.ModelSerializer):
    recorded_by = UserSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "visit", "amount", "method", "recorded_by", "paid_at"]
        read_only_fields = ["recorded_by", "paid_at"]

    def create(self, validated_data):
        validated_data["recorded_by"] = self.context["request"].user
        return super().create(validated_data)


# ---------------- Walk-in sales ----------------

class WalkInSaleItemSerializer(serializers.ModelSerializer):
    medicine = MedicineSerializer(read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.all(), source="medicine", write_only=True
    )
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = WalkInSaleItem
        fields = ["id", "medicine", "medicine_id", "quantity", "subtotal"]


class WalkInSaleSerializer(serializers.ModelSerializer):
    items = WalkInSaleItemSerializer(many=True)
    total = serializers.ReadOnlyField()
    sold_by = UserSerializer(read_only=True)

    class Meta:
        model = WalkInSale
        fields = ["id", "sold_by", "customer_name", "created_at", "items", "total"]
        read_only_fields = ["sold_by", "created_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        validated_data["sold_by"] = self.context["request"].user
        with transaction.atomic():
            sale = WalkInSale.objects.create(**validated_data)
            for item in items_data:
                medicine = item["medicine"]
                quantity = item["quantity"]
                WalkInSaleItem.objects.create(sale=sale, medicine=medicine, quantity=quantity)
                medicine.stock_quantity = max(0, medicine.stock_quantity - quantity)
                medicine.save(update_fields=["stock_quantity"])
        return sale
