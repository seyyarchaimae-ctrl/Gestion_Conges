from django.shortcuts import render
from .models import Team

def team_list(request):
    teams = Team.objects.prefetch_related('collaborators').all()
    return render(request, "teams/team_list.html", {"teams": teams})

def home(request):
    return render(request, 'teams/home.html')



from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Collaborator


@require_http_methods(["GET"])
def get_collaborators(request):
    collaborators = Collaborator.objects.all()
    
    data = []
    for collaborator in collaborators:
        data.append({
            'id': collaborator.id,
            'first_name': collaborator.first_name,
            'last_name': collaborator.last_name,
            'hire_date': collaborator.hire_date.isoformat() if collaborator.hire_date else None,
            'remaining_leave_balance': float(collaborator.remaining_leave_balance),
            'used_leave_balance': float(collaborator.used_leave_balance),
            'team': collaborator.team.project_name if collaborator.team else None
        })
    
    return JsonResponse({'collaborators': data})

def collaborators_page(request):
    return render(request, 'teams/collaborators.html')

@require_http_methods(["GET"])
def get_collaborator_profile(request, collaborator_id):
    try:
        collaborator = Collaborator.objects.get(id=collaborator_id)
        data = {
            'id': collaborator.id,
            'first_name': collaborator.first_name,
            'last_name': collaborator.last_name,
            'hire_date': collaborator.hire_date.isoformat() if collaborator.hire_date else None,
            'remaining_leave_balance': float(collaborator.remaining_leave_balance),
            'used_leave_balance': float(collaborator.used_leave_balance),
            'team': collaborator.team.project_name if collaborator.team else None
        }
        return JsonResponse(data)
    except Collaborator.DoesNotExist:
        return JsonResponse({'error': 'Collaborateur non trouvé'}, status=404)

@require_http_methods(["GET"])
def get_managers(request):
    teams_with_managers = Team.objects.filter(manager__isnull=False).select_related('manager')
    
    managers_data = []
    for team in teams_with_managers:
        manager = team.manager
        managers_data.append({
            'id': manager.id,
            'first_name': manager.first_name,
            'last_name': manager.last_name,
            'team_name': team.project_name
        })
    
    return JsonResponse(managers_data, safe=False)

def collaborator_profile_page(request, collaborator_id):
    return render(request, 'teams/collaborator_profile.html', {'collaborator_id': collaborator_id})

def managers_page(request):
    """Page qui affiche tous les managers disponibles"""
    # Récupérer toutes les équipes avec leurs managers
    teams_with_managers = Team.objects.filter(manager__isnull=False).select_related('manager')
    return render(request, 'teams/managers_page.html', {'teams': teams_with_managers})




from django.shortcuts import render, get_object_or_404
from .models import Collaborator, Team
from conges.models import DemandeConge

def manager_detail(request, manager_id):
    from django.contrib import messages
    from django.utils import timezone
    from django.db import transaction
    
    manager = get_object_or_404(Collaborator, id=manager_id)
    
    # Traitement des décisions de validation/refus
    if request.method == "POST":
        demande_id = request.POST.get("demande_id")
        decision = request.POST.get("decision")
        motif_refus = request.POST.get("motif_refus", "").strip()
        
        if demande_id:
            demande = get_object_or_404(DemandeConge, id=demande_id)
            
            with transaction.atomic():
                if decision == "VALIDEE":
                    demande.statut = "VALIDEE"
                    demande.date_validation = timezone.now()
                    
                    # Déduire les jours du solde du collaborateur
                    collaborateur = demande.collaborateur
                    collaborateur.remaining_leave_balance -= demande.nb_jours_demandes
                    collaborateur.used_leave_balance += demande.nb_jours_demandes
                    collaborateur.save()
                    
                    demande.save()
                    messages.success(
                        request, 
                        f"Demande de {demande.collaborateur.first_name} {demande.collaborateur.last_name} approuvée "
                        f"({demande.nb_jours_demandes} jours du {demande.date_debut} au {demande.date_fin})"
                    )
                
                elif decision == "REFUSEE":
                    if not motif_refus:
                        messages.error(request, "Veuillez saisir un motif de refus")
                    else:
                        demande.statut = "REFUSEE"
                        demande.date_refus = timezone.now()
                        demande.motif_refus = motif_refus
                        demande.save()
                        messages.warning(
                            request, 
                            f"Demande de {demande.collaborateur.first_name} {demande.collaborateur.last_name} refusée. "
                            f"Motif : {motif_refus}"
                        )
    
    # Récupérer les équipes et collaborateurs gérés par ce manager
    teams = Team.objects.filter(manager=manager)
    equipe = []
    for team in teams:
        for collab in team.collaborators.all():
            equipe.append({
                'nom': f"{collab.first_name} {collab.last_name}",
                'projet': team.project_name,
                'localisation': team.location,
                'used_leave_balance': collab.used_leave_balance,
                'remaining_leave_balance': collab.remaining_leave_balance
            })

    # Récupérer toutes les demandes EN_COURS des collaborateurs du manager
    demandes_en_cours = DemandeConge.objects.filter(
        collaborateur__team__manager=manager,
        statut='EN_COURS'
    ).order_by('date_debut')

    return render(request, 'teams/manager_detail.html', {
        'manager': manager,
        'equipe': equipe,
        'demandes': demandes_en_cours,
        'notifications': demandes_en_cours,  # pour compatibilité avec le template existant
        'nb_notifications': demandes_en_cours.count()
    })