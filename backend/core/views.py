from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ConsultationType, ICD10Code, DiagnosisNote, Medicine,
    Patient, Visit, Triage, Consultation, Prescription,
    Payment, WalkInSale, WalkInSaleItem,
)
from .serializers import (
    ConsultationTypeSerializer, ICD10CodeSerializer, DiagnosisNoteSerializer,
    MedicineSerializer, PatientSerializer, VisitSerializer, TriageSerializer,
    ConsultationSerializer, CompleteConsultationSerializer, PrescriptionSerializer,
    PaymentSerializer, WalkInSaleSerializer,
)
from .permissions import IsNurse, IsDoctor, IsAdminOrReadOnly, IsNurseOrReadOnly


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
    queryset = Patient.objects.all().order_by("-created_at")
    serializer_class = PatientSerializer
    permission_classes = [IsNurseOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "phone", "national_id"]


class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.select_related("patient", "consultation_type", "triage").order_by("-created_at")
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
    queryset = WalkInSale.objects.prefetch_related("items", "items__medicine").order_by("-created_at")
    serializer_class = WalkInSaleSerializer
    permission_classes = [IsNurseOrReadOnly]


# ---------------- Dashboard (shared by Doctor & Nurse, graphs) ----------------

class DashboardStatsView(APIView):
    """Aggregated stats for dashboard graphs. Available to any authenticated
    staff member (doctor/nurse/admin) — both roles see the same hospital-wide
    picture, just from different sidebars."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=29)

        # Visits per day (last 30 days)
        visits_by_day = (
            Visit.objects.filter(created_at__date__gte=thirty_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        # Revenue per day (last 30 days) - consultations + OTC sales
        revenue_by_day = (
            Payment.objects.filter(paid_at__date__gte=thirty_days_ago)
            .annotate(day=TruncDate("paid_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )

        # Top 5 most-prescribed/dispensed medicines (last 30 days, consultations + OTC)
        top_prescribed = (
            Prescription.objects.filter(consultation__started_at__date__gte=thirty_days_ago)
            .values("medicine__name")
            .annotate(quantity=Sum("quantity"))
            .order_by("-quantity")[:5]
        )

        # Visits by consultation type (all-time, for a breakdown chart)
        visits_by_type = (
            Visit.objects.values("consultation_type__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return Response({
            "total_patients": Patient.objects.count(),
            "total_visits": Visit.objects.count(),
            "visits_today": Visit.objects.filter(created_at__date=today).count(),
            "total_revenue": Payment.objects.aggregate(total=Sum("amount"))["total"] or 0,
            "revenue_today": Payment.objects.filter(paid_at__date=today).aggregate(total=Sum("amount"))["total"] or 0,
            "queue_length": Visit.objects.filter(status=Visit.Status.QUEUED).count(),
            "low_stock_medicines": Medicine.objects.filter(stock_quantity__lt=20).count(),
            "visits_by_day": [{"date": str(r["day"]), "count": r["count"]} for r in visits_by_day],
            "revenue_by_day": [{"date": str(r["day"]), "amount": float(r["total"])} for r in revenue_by_day],
            "top_medicines": [{"name": r["medicine__name"], "quantity": r["quantity"]} for r in top_prescribed],
            "visits_by_type": [{"name": r["consultation_type__name"], "count": r["count"]} for r in visits_by_type],
        })