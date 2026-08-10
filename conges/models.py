from django.db import models
from django.contrib.auth.models import User
from teams.models import Collaborator
from django.utils import timezone

class DemandeConge(models.Model):
    STATUT_CHOICES = [
        ('EN_COURS', 'En cours'),
        ('VALIDEE', 'Validée'),
        ('REFUSEE', 'Refusée'),
        ('ANNULEE', 'Annulée'),
    ]
    
    collaborateur = models.ForeignKey(Collaborator, on_delete=models.CASCADE, related_name='demandes_conges')
    date_debut = models.DateField()
    date_fin = models.DateField()
    commentaire = models.TextField(blank=True, null=True)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='EN_COURS')
    nb_jours_demandes = models.DecimalField(max_digits=5, decimal_places=1)
    demi_journee = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Calcul automatique du nombre de jours
        if self.demi_journee:
            self.nb_jours_demandes = 0.5
            # Pour une demi-journée, la date de fin est la même que la date de début
            if self.date_debut:
                self.date_fin = self.date_debut
        elif self.date_debut and self.date_fin:
            delta = self.date_fin - self.date_debut
            self.nb_jours_demandes = delta.days + 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Demande de {self.collaborateur} du {self.date_debut} au {self.date_fin}"
    
    def get_statut_display_color(self):
        """Retourne la couleur CSS correspondant au statut"""
        colors = {
            'EN_COURS': '#ffc107',  # Jaune
            'VALIDEE': '#28a745',   # Vert
            'REFUSEE': '#dc3545',   # Rouge
            'ANNULEE': '#6c757d',   # Gris
        }
        return colors.get(self.statut, '#6c757d')
    
    def get_statut_icon(self):
        """Retourne l'icône correspondant au statut"""
        icons = {
            'EN_COURS': '⏳',
            'VALIDEE': '✅',
            'REFUSEE': '❌',
            'ANNULEE': '🗑️',
        }
        return icons.get(self.statut, '❓')
    
    def is_en_cours(self):
        """Vérifie si la demande est en cours"""
        return self.statut == 'EN_COURS'
    
    def is_validee(self):
        """Vérifie si la demande est validée"""
        return self.statut == 'VALIDEE'
    
    def is_refusee(self):
        """Vérifie si la demande est refusée"""
        return self.statut == 'REFUSEE'

    def is_annulee(self):
        """Vérifie si la demande est annulée"""
        return self.statut == 'ANNULEE'
    
    def peut_etre_modifiee(self):
        """Vérifie si la demande peut encore être modifiée"""
        return self.statut == 'EN_COURS'
    
    def peut_etre_annulee(self):
        """Vérifie si la demande peut être annulée"""
        return self.statut == 'EN_COURS'
    
    def get_duree_readable(self):
        """Retourne la durée sous forme lisible"""
        if self.nb_jours_demandes == 0.5:
            return "0.5 jour"
        if self.nb_jours_demandes == 1:
            return "1 jour"
        return f"{self.nb_jours_demandes} jours"
    
    def get_periode_readable(self):
        """Retourne la période sous forme lisible"""
        if self.date_debut == self.date_fin:
            return f"le {self.date_debut.strftime('%d/%m/%Y')}"
        return f"du {self.date_debut.strftime('%d/%m/%Y')} au {self.date_fin.strftime('%d/%m/%Y')}"
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Demande de congé'
        verbose_name_plural = 'Demandes de congé'

class Conge(models.Model):
    TYPE_CHOICES = [
        ('CP', 'Congés Payés'),
        ('MALADIE', 'Congé Maladie'),
        ('SANS_SOLDE', 'Congé Sans Solde'),
        ('AUTRE', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('EN_ATTENTE', 'En Attente'),
        ('APPROUVE', 'Approuvé'),
        ('REFUSE', 'Refusé'),
    ]

    employe = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conges')
    type_conge = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_debut = models.DateField()
    date_fin = models.DateField()
    raison = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='EN_ATTENTE')
    
    date_demande = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    commentaire_admin = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_demande']
        verbose_name = 'Congé'
        verbose_name_plural = 'Congés'

    def __str__(self):
        return f"Congé de {self.employe.username} du {self.date_debut} au {self.date_fin}"

    def duree_conge(self):
        """Calcule la durée du congé en jours"""
        return (self.date_fin - self.date_debut).days + 1


class Notification(models.Model):
    """Modèle pour les notifications des managers"""
    
    TYPE_CHOICES = [
        ('NOUVELLE_DEMANDE', 'Nouvelle demande'),
        ('VALIDATION', 'Validation'),
        ('REFUS', 'Refus'),
        ('MODIFICATION', 'Modification'),
        ('ANNULATION', 'Annulation'),
    ]
    
    manager = models.ForeignKey(
        'teams.Collaborator', 
        on_delete=models.CASCADE,
        related_name='notifications_recues',
        help_text="Manager qui recevra la notification"
    )
    
    demande_conge = models.ForeignKey(
        DemandeConge, 
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="Demande de congé concernée"
    )
    
    type_notification = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='NOUVELLE_DEMANDE',
        help_text="Type de notification"
    )
    
    message = models.TextField(
        help_text="Message de la notification"
    )
    
    date_creation = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création de la notification"
    )
    
    lu = models.BooleanField(
        default=False,
        help_text="Indique si la notification a été lue"
    )
    
    date_lecture = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date de lecture de la notification"
    )
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['manager', 'lu']),
            models.Index(fields=['date_creation']),
        ]
    
    def __str__(self):
        return f"Notification pour {self.manager} - {self.type_notification}"
    
    def get_type_display_color(self):
        """Retourne la couleur CSS correspondant au type de notification"""
        colors = {
            'NOUVELLE_DEMANDE': '#007bff',  # Bleu
            'VALIDATION': '#28a745',        # Vert
            'REFUS': '#dc3545',            # Rouge
            'MODIFICATION': '#ffc107',      # Jaune
            'ANNULATION': '#6c757d',       # Gris
        }
        return colors.get(self.type_notification, '#007bff')
    
    def get_type_display_icon(self):
        """Retourne l'icône FontAwesome correspondant au type"""
        icons = {
            'NOUVELLE_DEMANDE': 'fas fa-plus-circle',
            'VALIDATION': 'fas fa-check-circle', 
            'REFUS': 'fas fa-times-circle',
            'MODIFICATION': 'fas fa-edit',
            'ANNULATION': 'fas fa-ban',
        }
        return icons.get(self.type_notification, 'fas fa-bell')
    
    def get_formatted_date_creation(self):
        """Retourne la date de création formatée"""
        return self.date_creation.strftime("%d/%m/%Y à %H:%M")
    
    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        from django.utils import timezone
        self.lu = True
        self.date_lecture = timezone.now()
        self.save(update_fields=['lu', 'date_lecture'])
    
    def get_time_since_creation(self):
        """Retourne le temps écoulé depuis la création"""
        from django.utils.timesince import timesince
        return timesince(self.date_creation, timezone.now())


def create_notification(demande_conge, type_notification='NOUVELLE_DEMANDE', message_personnalise=None):
    """
    Fonction utilitaire pour créer une notification automatique
    
    Args:
        demande_conge: Instance de DemandeConge
        type_notification: Type de notification (NOUVELLE_DEMANDE, VALIDATION, etc.)
        message_personnalise: Message personnalisé (optionnel)
    
    Returns:
        Notification: Instance de notification créée
    """
    # Récupération du manager de l'équipe du collaborateur
    collaborateur = demande_conge.collaborateur
    team = collaborateur.team
    manager = team.manager if team else None
    
    if not manager:
        # Si pas de manager défini, prendre le premier collaborateur de l'équipe
        if team and team.members.exists():
            manager = team.members.first()
        else:
            # Si aucun manager, ne pas créer de notification
            return None
    
    # Génération du message automatique si pas de message personnalisé
    if not message_personnalise:
        messages = {
            'NOUVELLE_DEMANDE': f"Nouvelle demande de congé de {collaborateur.first_name} {collaborateur.last_name} "
                               f"{demande_conge.get_periode_readable()} "
                               f"({demande_conge.get_duree_readable()}).",
            
            'VALIDATION': f"Demande de congé #{demande_conge.id} de {collaborateur.first_name} {collaborateur.last_name} "
                         f"a été validée.",
            
            'REFUS': f"Demande de congé #{demande_conge.id} de {collaborateur.first_name} {collaborateur.last_name} "
                    f"a été refusée.",
            
            'MODIFICATION': f"Demande de congé #{demande_conge.id} de {collaborateur.first_name} {collaborateur.last_name} "
                           f"a été modifiée.",
            
            'ANNULATION': f"Demande de congé #{demande_conge.id} de {collaborateur.first_name} {collaborateur.last_name} "
                         f"a été annulée.",
        }
        message_personnalise = messages.get(type_notification, f"Notification concernant la demande #{demande_conge.id}")
    
    # Création de la notification
    notification = Notification.objects.create(
        manager=manager,
        demande_conge=demande_conge,
        type_notification=type_notification,
        message=message_personnalise
    )
    
    return notification


def get_manager_notifications_count(manager, non_lues_seulement=True):
    """
    Récupère le nombre de notifications pour un manager
    
    Args:
        manager: Instance de Collaborator (manager)
        non_lues_seulement: Si True, compte seulement les notifications non lues
    
    Returns:
        int: Nombre de notifications
    """
    queryset = Notification.objects.filter(manager=manager)
    if non_lues_seulement:
        queryset = queryset.filter(lu=False)
    return queryset.count()


def marquer_toutes_notifications_comme_lues(manager):
    """
    Marque toutes les notifications d'un manager comme lues
    
    Args:
        manager: Instance de Collaborator (manager)
    
    Returns:
        int: Nombre de notifications marquées comme lues
    """
    notifications_non_lues = Notification.objects.filter(manager=manager, lu=False)
    count = notifications_non_lues.count()
    
    notifications_non_lues.update(
        lu=True,
        date_lecture=timezone.now()
    )
    
    return count

class HistoriqueModification(models.Model):
    ACTION_CHOICES = [
        ('MODIFICATION', 'Modification'),
        ('ANNULATION', 'Annulation'),
    ]

    demande = models.ForeignKey(DemandeConge, on_delete=models.CASCADE, related_name='historique')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ancienne_valeur = models.TextField(blank=True, null=True)
    nouvelle_valeur = models.TextField(blank=True, null=True)
    date_action = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    motif = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_action_display()} de la demande {self.demande.id} par {self.auteur} le {self.date_action}"
