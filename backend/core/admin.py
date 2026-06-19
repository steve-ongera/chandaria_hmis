from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, ConsultationType, ICD10Code, DiagnosisNote, Medicine,
    Patient, Visit, Triage, Consultation, ConsultationNote,
    Prescription, Payment, WalkInSale, WalkInSaleItem,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("role",)}),)
    list_display = ["username", "first_name", "last_name", "role", "is_staff"]


admin.site.register(ConsultationType)
admin.site.register(ICD10Code)
admin.site.register(DiagnosisNote)
admin.site.register(Medicine)
admin.site.register(Patient)
admin.site.register(Visit)
admin.site.register(Triage)
admin.site.register(Consultation)
admin.site.register(ConsultationNote)
admin.site.register(Prescription)
admin.site.register(Payment)
admin.site.register(WalkInSale)
admin.site.register(WalkInSaleItem)
