from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ConsultationType, ICD10Code, DiagnosisNote, Medicine,
    Patient, Visit, Triage, Consultation, Prescription,
    Payment, WalkInSale,
)
from .serializers import (
    ConsultationTypeSerializer, ICD10CodeSerializer, DiagnosisNoteSerializer,
    MedicineSerializer, PatientSerializer, VisitSerializer, TriageSerializer,
    ConsultationSerializer, CompleteConsultationSerializer, PrescriptionSerializer,
    PaymentSerializer, WalkInSaleSerializer,
)
from .permissions import IsNurse, IsDoctor, IsAdminOrReadOnly


# ---------------- Lookup tables (admin manages, everyone reads) ----------------

class ConsultationTypeViewSet(viewsets.ModelViewSet):
    queryset = ConsultationType.objects.filter(is_active=True)
    serializer_class = ConsultationTypeSerializer
    permission_classes = [IsAdminOrReadOnly]


class ICD10CodeViewSet(viewsets.ModelViewSet):
    queryset = ICD10Code.objects.all()
    serializer_class = ICD10CodeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["code", "description"]


class DiagnosisNoteViewSet(viewsets.ModelViewSet):
    queryset = DiagnosisNote.objects.filter(is_active=True)
    serializer_class = DiagnosisNoteSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["title"]


class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


# ---------------- Patient / Reception (Nurse) ----------------

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsNurse]
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "phone", "national_id"]


class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.select_related("patient", "consultation_type", "triage").all()
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated]  # nurse creates, doctor reads queue
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "patient"]

    @action(detail=False, methods=["get"], url_path="queue")
    def queue(self, request):
        """Doctor's consultation queue: visits that have been triaged and queued."""
        visits = self.get_queryset().filter(status=Visit.Status.QUEUED).order_by("created_at")
        serializer = self.get_serializer(visits, many=True)
        return Response(serializer.data)


class TriageViewSet(viewsets.ModelViewSet):
    queryset = Triage.objects.select_related("visit", "nurse").all()
    serializer_class = TriageSerializer
    permission_classes = [IsNurse]


# ---------------- Consultation (Doctor) ----------------

class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.select_related(
        "visit", "visit__patient", "visit__consultation_type", "visit__triage", "doctor"
    ).prefetch_related("icd10_codes", "consultation_notes", "prescriptions")
    serializer_class = ConsultationSerializer
    permission_classes = [IsDoctor]

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        consultation = self.get_object()
        serializer = CompleteConsultationSerializer(
            data={}, context={"consultation": consultation, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ConsultationSerializer(consultation).data)

    @action(detail=True, methods=["post"], url_path="add-note")
    def add_note(self, request, pk=None):
        """Attach a diagnosis/service note (predefined or custom) with an amount."""
        consultation = self.get_object()
        from .models import ConsultationNote
        diagnosis_note_id = request.data.get("diagnosis_note")
        custom_title = request.data.get("custom_title", "")
        amount = request.data.get("amount")
        note = ConsultationNote.objects.create(
            consultation=consultation,
            diagnosis_note_id=diagnosis_note_id or None,
            custom_title=custom_title,
            amount=amount,
        )
        return Response({"id": note.id, "title": note.title, "amount": note.amount},
                         status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="prescribe")
    def prescribe(self, request, pk=None):
        """Add a prescription line item (medicine + quantity) to this consultation."""
        consultation = self.get_object()
        serializer = PrescriptionSerializer(data={**request.data, "consultation": consultation.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(consultation=consultation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PrescriptionViewSet(viewsets.ModelViewSet):
    """Mainly used by nurses to dispense medicine at reception/billing stage."""
    queryset = Prescription.objects.select_related("medicine", "consultation").all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="dispense")
    def dispense(self, request, pk=None):
        prescription = self.get_object()
        if prescription.dispensed:
            return Response({"detail": "Already dispensed."}, status=status.HTTP_400_BAD_REQUEST)
        medicine = prescription.medicine
        if medicine.stock_quantity < prescription.quantity:
            return Response({"detail": "Insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)
        medicine.stock_quantity -= prescription.quantity
        medicine.save(update_fields=["stock_quantity"])
        prescription.dispensed = True
        prescription.dispensed_by = request.user
        prescription.dispensed_at = timezone.now()
        prescription.save(update_fields=["dispensed", "dispensed_by", "dispensed_at"])
        return Response(PrescriptionSerializer(prescription).data)


# ---------------- Billing (Nurse) ----------------

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("visit", "recorded_by").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsNurse]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["visit"]


class WalkInSaleViewSet(viewsets.ModelViewSet):
    queryset = WalkInSale.objects.prefetch_related("items", "items__medicine").all()
    serializer_class = WalkInSaleSerializer
    permission_classes = [IsNurse]
