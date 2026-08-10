// Fonction pour gérer la soumission du formulaire de congés
function submitLeaveRequest(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());
    
    fetch('/api/conges/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Demande de congés envoyée avec succès!');
            window.location.reload();
        } else {
            alert('Erreur lors de l\'envoi de la demande');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Une erreur est survenue');
    });
}

// Fonction pour obtenir le cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fonction pour charger les congés
function loadLeaves() {
    fetch('/api/conges/')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#leaves-table tbody');
            tableBody.innerHTML = '';
            
            data.forEach(leave => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${leave.start_date}</td>
                    <td>${leave.end_date}</td>
                    <td>${leave.type}</td>
                    <td><span class="badge badge-${leave.status.toLowerCase()}">${leave.status}</span></td>
                    <td>${leave.reason}</td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => console.error('Error:', error));
}

// Écouteurs d'événements
document.addEventListener('DOMContentLoaded', function() {
    const leaveForm = document.getElementById('leave-form');
    if (leaveForm) {
        leaveForm.addEventListener('submit', submitLeaveRequest);
    }
    
    // Charger les congés au chargement de la page
    loadLeaves();
});