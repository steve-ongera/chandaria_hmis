from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("consultation-types", views.ConsultationTypeViewSet)
router.register("icd10-codes", views.ICD10CodeViewSet)
router.register("diagnosis-notes", views.DiagnosisNoteViewSet)
router.register("medicines", views.MedicineViewSet)
router.register("patients", views.PatientViewSet)
router.register("visits", views.VisitViewSet)
router.register("triage", views.TriageViewSet)
router.register("consultations", views.ConsultationViewSet)
router.register("prescriptions", views.PrescriptionViewSet)
router.register("payments", views.PaymentViewSet)
router.register("walkin-sales", views.WalkInSaleViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
