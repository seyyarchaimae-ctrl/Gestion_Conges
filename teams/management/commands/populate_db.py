from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teams.models import Team, Collaborator
from conges.models import DemandeConge
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Populate database with dummy data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Cleaning database...')
        
        # Delete all existing data
        DemandeConge.objects.all().delete()
        Collaborator.objects.all().delete()
        Team.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

        self.stdout.write('Creating Teams...')
        teams_data = [
            {'name': 'Développement Mobile', 'location': 'Paris'},
            {'name': 'Backend Services', 'location': 'Lyon'},
            {'name': 'Design & UI', 'location': 'Bordeaux'},
        ]
        
        teams = []
        for t_data in teams_data:
            team = Team.objects.create(project_name=t_data['name'], location=t_data['location'])
            teams.append(team)

        self.stdout.write('Creating Managers...')
        managers_data = [
            {'first': 'Jean', 'last': 'Dupont', 'team_idx': 0},
            {'first': 'Marie', 'last': 'Curie', 'team_idx': 1},
            {'first': 'Pierre', 'last': 'Martin', 'team_idx': 2},
        ]

        for m_data in managers_data:
            # Create User
            username = f"{m_data['first'].lower()}.{m_data['last'].lower()}"
            user = User.objects.create_user(username=username, password='password123', email=f"{username}@example.com")
            
            # Create Collaborator (Manager)
            manager = Collaborator.objects.create(
                first_name=m_data['first'],
                last_name=m_data['last'],
                hire_date=date(2020, 1, 1),
                team=teams[m_data['team_idx']],
                remaining_leave_balance=32.0,
                used_leave_balance=0.0
            )
            
            # Assign as manager of the team
            team = teams[m_data['team_idx']]
            team.manager = manager
            team.save()
            
            self.stdout.write(f"Created Manager: {manager} for {team}")

        self.stdout.write('Creating Collaborators...')
        collaborators_data = [
            {'first': 'Sophie', 'last': 'Bernard', 'team_idx': 0},
            {'first': 'Lucas', 'last': 'Petit', 'team_idx': 0},
            {'first': 'Thomas', 'last': 'Richard', 'team_idx': 1},
            {'first': 'Emma', 'last': 'Durand', 'team_idx': 1},
            {'first': 'Julie', 'last': 'Moreau', 'team_idx': 2},
            {'first': 'Nicolas', 'last': 'Lefebvre', 'team_idx': 2},
            {'first': 'Camille', 'last': 'Leroy', 'team_idx': 0},
            {'first': 'Antoine', 'last': 'Roux', 'team_idx': 1},
        ]

        collaborators = []
        for c_data in collaborators_data:
            # Create User (optional for collaborators if they don't login, but better if they do)
            # Assuming collaborators might not have login in this system or share same model? 
            # The model `Collaborator` is not OneToOne with User in the provided code snippet, 
            # but `conges.models.DemandeConge` links to `Collaborator`.
            # Wait, `conges.views.home` uses `request.user`. 
            # Let's check `conges/models.py` again. 
            # `Conge` model in `views.py` seems to be different from `DemandeConge`.
            # In `views.py`: `conge = Conge.objects.create(employe=request.user...)`
            # But `DemandeConge` links to `Collaborator`.
            # There seems to be a disconnect or I missed something.
            # Let's look at `conges/views.py` again.
            # `demande_conge_form` takes `collaborator_id`.
            # It seems the system might be designed where a Manager creates requests for Collaborators?
            # Or Collaborators are linked to Users?
            # Let's check `teams/models.py` again.
            # `Collaborator` does NOT have a User field in the snippet I read.
            # However, `conges/views.py` uses `request.user` for `home` view but `collaborator_id` for `demande_conge_form`.
            # Let's assume for now Collaborators are just records.
            
            collab = Collaborator.objects.create(
                first_name=c_data['first'],
                last_name=c_data['last'],
                hire_date=date(2022, 5, 15),
                team=teams[c_data['team_idx']],
                remaining_leave_balance=32.0,
                used_leave_balance=0.0
            )
            collaborators.append(collab)
            self.stdout.write(f"Created Collaborator: {collab}")

        self.stdout.write('Creating Leave Requests...')
        
        statuses = ['EN_COURS', 'VALIDEE', 'REFUSEE', 'ANNULEE']
        
        today = date.today()
        
        for collab in collaborators:
            # Create 2-3 requests per collaborator
            for _ in range(random.randint(2, 4)):
                start_offset = random.randint(-30, 60)
                duration = random.randint(1, 5)
                is_half = random.choice([True, False]) if duration == 1 else False
                
                start_date = today + timedelta(days=start_offset)
                
                if is_half:
                    end_date = start_date
                    nb_jours = 0.5
                else:
                    end_date = start_date + timedelta(days=duration-1)
                    nb_jours = duration
                
                statut = random.choice(statuses)
                
                DemandeConge.objects.create(
                    collaborateur=collab,
                    date_debut=start_date,
                    date_fin=end_date,
                    commentaire=f"Congé {random.choice(['vacances', 'maladie', 'famille'])}",
                    statut=statut,
                    nb_jours_demandes=nb_jours,
                    demi_journee=is_half
                )

        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))
