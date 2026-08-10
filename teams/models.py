from django.db import models

class Team(models.Model):
    project_name = models.CharField(max_length=255)
    location = models.CharField(max_length=100)
    manager = models.ForeignKey('Collaborator', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_teams')

    def __str__(self):
        return self.project_name
    
    @property 
    def members(self):
        return self.collaborators

class Collaborator(models.Model):
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    hire_date = models.DateField(null=True, blank=True)
    remaining_leave_balance = models.DecimalField(max_digits=5, decimal_places=1, default=32.0)
    used_leave_balance = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="collaborators")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @classmethod
    def reset_annual_leave(cls):
        """Réinitialise le solde de congés annuel pour tous les collaborateurs"""
        return cls.objects.update(
            remaining_leave_balance=32.0,
            used_leave_balance=0.0
        )
