from django.contrib import admin
from .models import Conge

@admin.register(Conge)
class CongeAdmin(admin.ModelAdmin):
    list_display = ('employe', 'type_conge', 'date_debut', 'date_fin', 'status', 'date_demande')
    list_filter = ('status', 'type_conge', 'date_demande')
    search_fields = ('employe__username', 'raison')
    readonly_fields = ('date_demande', 'date_modification')
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('employe', 'type_conge', 'date_debut', 'date_fin', 'raison')
        }),
        ('Status', {
            'fields': ('status', 'commentaire_admin')
        }),
        ('Dates', {
            'fields': ('date_demande', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
