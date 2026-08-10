from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Conge, DemandeConge, HistoriqueModification, create_notification
from teams.models import Collaborator
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

def calculer_jours_ouvrables(date_debut, date_fin):
    """
    Calcule le nombre de jours ouvrables entre deux dates (exclut samedi et dimanche)
    """
    jours_ouvrables = 0
    current_date = date_debut
    
    while current_date <= date_fin:
        # 0 = Lundi, 6 = Dimanche
        if current_date.weekday() < 5:  # Lundi à Vendredi
            jours_ouvrables += 1
        current_date += timedelta(days=1)
    
    return jours_ouvrables

def home(request):
    """Page d'accueil"""
    if request.user.is_authenticated:
        conges = Conge.objects.filter(employe=request.user).order_by('-date_demande')[:5]
    else:
        conges = []
    return render(request, 'conges/home.html', {'conges': conges})

# @login_required
def conges_list(request):
    """Liste des congés de l'utilisateur"""
    conges = Conge.objects.filter(employe=request.user).order_by('-date_demande')
    return render(request, 'conges/conges_list.html', {'conges': conges})

# @login_required
def conge_new(request):
    """Création d'une nouvelle demande de congé"""
    if request.method == "POST":
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')
        type_conge = request.POST.get('type_conge')
        raison = request.POST.get('raison')
        
        conge = Conge.objects.create(
            employe=request.user,
            date_debut=date_debut,
            date_fin=date_fin,
            type_conge=type_conge,
            raison=raison,
            status='EN_ATTENTE'
        )
        
        messages.success(request, 'Votre demande de congé a été enregistrée.')
        return redirect('conges_list')

    return render(request, 'conges/conge_form.html')

# @login_required
def conge_detail(request, pk):
    """Détails d'un congé"""
    conge = get_object_or_404(Conge, pk=pk, employe=request.user)
    return render(request, 'conges/conge_detail.html', {'conge': conge})

# @login_required
def demande_conge_form(request, collaborator_id):
    """Formulaire de demande de congé avec validation complète et transaction atomique"""
    # Récupérer le collaborateur par ID
    collaborator = get_object_or_404(Collaborator, id=collaborator_id)
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        date_debut = request.POST.get('date_debut')
        date_fin = request.POST.get('date_fin')
        motif = request.POST.get('commentaire', '').strip()
        demi_journee = request.POST.get('demi_journee') == 'on'
        
        # Liste pour collecter les erreurs
        errors = []
        
        # Validation des dates
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            if demi_journee:
                date_fin_obj = date_debut_obj
            else:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errors.append("Les dates fournies ne sont pas valides.")
            date_debut_obj = date_fin_obj = None
        
        if date_debut_obj and date_fin_obj:
            # Validation 1: Les dates ne doivent pas être dans le passé
            today = date.today()
            if date_debut_obj < today:
                errors.append("La date de début ne peut pas être dans le passé.")
            if not demi_journee and date_fin_obj < today:
                errors.append("La date de fin ne peut pas être dans le passé.")
            
            # Validation 2: La date de fin doit être postérieure ou égale à la date de début
            if not demi_journee and date_fin_obj < date_debut_obj:
                errors.append("La date de fin doit être postérieure ou égale à la date de début.")
            
            # Validation 3: Maximum 30 jours de congé consécutifs
            if (date_fin_obj - date_debut_obj).days >= 30:
                errors.append("Une demande de congé ne peut pas dépasser 30 jours consécutifs.")
            
            # Validation 4: Délai minimum de 15 jours entre la demande et le début du congé
            delai_demande = (date_debut_obj - today).days
            if delai_demande < 15:
                errors.append("Les demandes de congé doivent être soumises au moins 15 jours à l'avance.")
            
            # Validation 5: Vérification du solde de congés
            if demi_journee:
                nb_jours_demandes = 0.5
            else:
                nb_jours_demandes = (date_fin_obj - date_debut_obj).days + 1
                
            if nb_jours_demandes > collaborator.remaining_leave_balance:
                errors.append(f"Solde de congés insuffisant. Vous avez {collaborator.remaining_leave_balance} jours disponibles, mais vous demandez {nb_jours_demandes} jours.")
            
            # Validation 6: Vérification de chevauchement avec d'autres demandes
            demandes_existantes = DemandeConge.objects.filter(
                collaborateur=collaborator,
                statut__in=['EN_COURS', 'VALIDEE']
            )
            
            for demande in demandes_existantes:
                if not (date_fin_obj < demande.date_debut or date_debut_obj > demande.date_fin):
                    errors.append(f"Cette période chevauche avec une demande existante du {demande.date_debut} au {demande.date_fin}.")
        
        # Validation du motif
        # if not motif:
        #     errors.append("Le motif est obligatoire.")
        # elif len(motif) < 10:
        #     errors.append("Le motif doit contenir au moins 10 caractères.")
        # elif len(motif) > 500:
        #     errors.append("Le motif ne peut pas dépasser 500 caractères.")
        
        # Si des erreurs existent, les afficher
        if errors:
            for error in errors:
                messages.error(request, error)
            
            context = {
                'collaborator': collaborator,
                'form_data': {
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'motif': motif,
                    'demi_journee': demi_journee
                }
            }
            return render(request, 'conges/demande_conge_form.html', context)
        
        # Si toutes les validations passent, créer la demande de congé avec transaction atomique
        try:
            with transaction.atomic():
                # Création de la demande de congé avec statut EN_COURS
                demande = DemandeConge.objects.create(
                    collaborateur=collaborator,
                    date_debut=date_debut_obj,
                    date_fin=date_fin_obj,
                    commentaire=motif,
                    statut='EN_COURS',
                    demi_journee=demi_journee
                )
                
                # Log de la création
                logger.info(f"Nouvelle demande de congé créée - ID: {demande.id}, Collaborateur: {collaborator.first_name} {collaborator.last_name}, Période: {date_debut_obj} au {date_fin_obj}")
                
                # Message de succès avec détails
                nb_jours = demande.nb_jours_demandes
                messages.success(
                    request, 
                    f"Votre demande de congé a été soumise avec succès ! "
                    f"Référence: #{demande.id} - {demande.get_duree_readable()} "
                    f"{demande.get_periode_readable()}. "
                    f"Statut: En cours d'examen."
                )
                
                return redirect('collaborator_profile_page', collaborator_id=collaborator.id)
                
        except ValidationError as e:
            logger.error(f"Erreur de validation lors de la création de la demande: {e}")
            messages.error(request, f"Erreur lors de la création de la demande: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la création de la demande: {e}")
            messages.error(request, "Une erreur inattendue s'est produite. Veuillez réessayer.")
        
        # Retour au formulaire en cas d'erreur
        context = {
            'collaborator': collaborator,
            'form_data': {
                'date_debut': date_debut,
                'date_fin': date_fin,
                'motif': motif
            }
        }
        return render(request, 'conges/demande_conge_form.html', context)
        
    context = {
        'collaborator': collaborator,
    }
    return render(request, 'conges/demande_conge_form.html', context)

# @login_required
def historique_demandes(request, collaborator_id):
    """Affichage de l'historique des demandes de congé du collaborateur"""
    # Récupérer le collaborateur par ID
    collaborator = get_object_or_404(Collaborator, id=collaborator_id)
    
    demandes = DemandeConge.objects.filter(collaborateur=collaborator).order_by('-date_creation')
    
    context = {
        'collaborator': collaborator,
        'demandes': demandes
    }
    return render(request, 'conges/historique_demandes.html', context)


# team/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import DemandeConge

def liste_demandes_manager(request):
    demandes = DemandeConge.objects.filter(statut="EN_COURS").order_by('date_debut')
    return render(request, "teams/liste_demandes_manager.html", {"demandes": demandes})

from django.contrib import messages
from django.utils import timezone
@transaction.atomic
def decision_manager(request, demande_id):
    demande = get_object_or_404(DemandeConge, id=demande_id)

    if request.method == "POST":
        decision = request.POST.get("decision")
        motif = request.POST.get("motif_refus", "").strip()

        if decision == "VALIDEE":
            demande.statut = "VALIDEE"
            demande.date_validation = timezone.now()
            collaborateur = demande.collaborateur   # récupérer l'objet
            collaborateur.remaining_leave_balance -= demande.nb_jours_demandes
            collaborateur.used_leave_balance += demande.nb_jours_demandes
            collaborateur.save()                   # sauvegarder dans la DB

            demande.save()
            
            messages.success(
                request, 
                f"Votre demande de congé de {demande.nb_jours_demandes } jours du {demande.date_debut} au {demande.date_fin} a été approuvée."
            )
        
        elif decision == "REFUSEE":
            if not motif:
                messages.error(request, "Veuillez saisir un motif de refus ❌")
                return redirect("conges:liste_demandes_manager")
            demande.statut = "REFUSEE"
            demande.date_refus = timezone.now()
            demande.motif_refus = motif
            demande.save()
            messages.warning(request, f"Demande refusée. Motif : {motif}")

    return redirect("conges:liste_demandes_manager")

def modifier_demande(request, pk):
    """Modification d'une demande de congé (uniquement la date de fin)"""
    demande = get_object_or_404(DemandeConge, pk=pk)
    
    # Vérification que la demande est en cours
    if not demande.peut_etre_modifiee():
        messages.error(request, "Cette demande ne peut plus être modifiée.")
        return redirect('conges:historique_demandes', collaborator_id=demande.collaborateur.id)
        
    if request.method == 'POST':
        date_fin = request.POST.get('date_fin')
        motif = request.POST.get('motif')
        
        if not motif:
            messages.error(request, "Le motif de la modification est obligatoire.")
            return render(request, 'conges/modifier_demande.html', {'demande': demande})
            
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            
            # Validation: date fin >= date debut
            if date_fin_obj < demande.date_debut:
                messages.error(request, "La date de fin doit être postérieure à la date de début.")
                return render(request, 'conges/modifier_demande.html', {'demande': demande})
                
            # Sauvegarde des anciennes valeurs pour l'historique
            ancienne_valeur = f"Date fin: {demande.date_fin}, Jours: {demande.nb_jours_demandes}"
            
            # Mise à jour de la demande
            demande.date_fin = date_fin_obj
            demande.save() # Le calcul des jours se fait dans save()
            
            nouvelle_valeur = f"Date fin: {demande.date_fin}, Jours: {demande.nb_jours_demandes}"
            
            # Création de l'historique
            HistoriqueModification.objects.create(
                demande=demande,
                action='MODIFICATION',
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                auteur=request.user if request.user.is_authenticated else None,
                motif=motif
            )
            
            # Notification au manager
            create_notification(demande, 'MODIFICATION')
            
            messages.success(request, "La demande a été modifiée avec succès.")
            return redirect('conges:historique_demandes', collaborator_id=demande.collaborateur.id)
            
        except ValueError:
            messages.error(request, "Format de date invalide.")
            
    return render(request, 'conges/modifier_demande.html', {'demande': demande})

def annuler_demande(request, pk):
    """Annulation d'une demande de congé"""
    demande = get_object_or_404(DemandeConge, pk=pk)
    
    # Vérification que la demande est en cours
    if not demande.peut_etre_annulee():
        messages.error(request, "Cette demande ne peut plus être annulée.")
        return redirect('conges:historique_demandes', collaborator_id=demande.collaborateur.id)
        
    if request.method == 'POST':
        motif = "Annulé par collaborateur"
        
        # Sauvegarde de l'état avant annulation
        ancienne_valeur = f"Statut: {demande.statut}"
        
        # Mise à jour du statut
        demande.statut = 'ANNULEE'
        demande.save()
        
        # Création de l'historique
        HistoriqueModification.objects.create(
            demande=demande,
            action='ANNULATION',
            ancienne_valeur=ancienne_valeur,
            nouvelle_valeur="Statut: ANNULEE",
            auteur=request.user if request.user.is_authenticated else None,
            motif=motif
        )
        
        # Notification au manager
        create_notification(demande, 'ANNULATION')
        
        messages.success(request, "La demande a été annulée avec succès.")
        return redirect('conges:historique_demandes', collaborator_id=demande.collaborateur.id)
        
    return render(request, 'conges/annuler_demande_confirm.html', {'demande': demande})